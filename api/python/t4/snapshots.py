import copy
from enum import Enum
import hashlib
import json
import pathlib
import os

import shutil
import tempfile
import time

from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import url2pathname

import boto3
import jsonlines

from pathlib import Path
from .data_transfer import (copy_object, deserialize_obj, download_bytes, download_file, list_objects,
                            list_object_versions, upload_bytes, upload_file, TargetType)

from .exceptions import PackageException
from .util import HeliumException, split_path, BASE_PATH

SNAPSHOT_PREFIX = ".quilt/snapshots"

s3_client = boto3.client('s3')

def _make_prefix(key):
    return "%s/" % key.rstrip('/')


def _snapshot_path(tophash, path):
    bucket, prefix = split_path(path)
    return f'{bucket}/{SNAPSHOT_PREFIX}/{tophash}/{prefix}'


def _lookup_snapshot_path(bucket, tophash):
    snapshot_files = list_objects(f'{bucket}/{SNAPSHOT_PREFIX}/{tophash}')

    if not snapshot_files:
        raise HeliumException(f"Snapshot {tophash} not found")
    elif len(snapshot_files) > 1:
        raise HeliumException(f"Ambiguous snapshot hash: {tophash}")
    else:
        snapshot_file_key = snapshot_files[0]['Key']
        return f'{bucket}/{snapshot_file_key}'


def _parse_snapshot_path(snapshot_file_key):
    parts = snapshot_file_key.split('/')
    uid = parts[2]
    path = "/".join(parts[3:])
    return uid, path


def _parse_version_id(s3_url):
    # Parse the version ID the way the Java SDK does:
    # https://github.com/aws/aws-sdk-java/blob/master/aws-java-sdk-s3/src/main/java/com/amazonaws/services/s3/AmazonS3URI.java#L192
    query = parse_qs(s3_url.query)
    return query.get('versionId', [None])[0]


def _fix_url(url):
    """Convert non-URL paths to file:// URLs"""
    # TODO: Do something about file paths like C:\Users\foo if we care about Windows.
    parsed = urlparse(url)
    if not parsed.scheme:
        url = pathlib.Path(url).resolve().as_uri()
    return url


def _copy_file(src, dest, meta):
    src_url = urlparse(src)
    dest_url = urlparse(dest)
    if src_url.scheme == 'file':
        if dest_url.scheme == 'file':
            # TODO: metadata
            shutil.copyfile(url2pathname(src_url.path), url2pathname(dest_url.path))
        elif dest_url.scheme == 's3':
            upload_file(url2pathname(src_url.path), dest_url.netloc + unquote(dest_url.path), meta)
        else:
            raise NotImplementedError
    elif src_url.scheme == 's3':
        version_id = _parse_version_id(src_url)
        if dest_url.scheme == 'file':
            # TODO: metadata
            download_file(src_url.netloc + unquote(src_url.path), url2pathname(dest_url.path), version_id)
        elif dest_url.scheme == 's3':
            copy_object(src_url.netloc + unquote(src_url.path), dest_url.netloc + unquote(dest_url.path), meta, version_id)
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError

def read_snapshot_by_key(snapshot_file_key):
    if snapshot_file_key is None:
        snapshot_objs = {}
    else:
        snapshot_file, meta = download_bytes(snapshot_file_key)
        snapshot_objs = json.loads(snapshot_file.decode('utf8'))

    assert type(snapshot_objs) is dict
    return snapshot_objs


def read_latest_snapshot(path):
    """
    Find the most recent snapshot that contains the given path
    """
    bucket, prefix = split_path(path)
    snapshots = list_objects(f'{bucket}/{SNAPSHOT_PREFIX}/')
    snapshot_files = sorted(snapshots, key=lambda k: k['LastModified'], reverse=True)

    snapshot_file_key = None
    for snapshot in snapshot_files:
        key = snapshot['Key']
        uid, snap_path = _parse_snapshot_path(key)
        if _make_prefix(prefix).startswith(_make_prefix(snap_path)):
            snapshot_file_key = key
    full_key = f'{bucket}/{snapshot_file_key}' if snapshot_file_key else None
    snapshot = read_snapshot_by_key(full_key)
    uid, snapshot_path = _parse_snapshot_path(snapshot_file_key)
    snapshot.update(dict(path=snapshot_path))
    return snapshot


def read_snapshot_by_hash(bucket, snapshothash):
    snapshot_file_key = _lookup_snapshot_path(bucket, snapshothash)
    _, local_key = split_path(snapshot_file_key)
    uid, snapshot_path = _parse_snapshot_path(local_key)
    snapshot = read_snapshot_by_key(snapshot_file_key)
    snapshot.update(dict(path=snapshot_path))
    return snapshot


def get_snapshots(bucket, prefix):
    snapshot_files = list_objects(f'{bucket}/{SNAPSHOT_PREFIX}')

    snapshots_list = []
    for snapshot_rec in sorted(snapshot_files, key=lambda k: k['LastModified'], reverse=True):
        snapshot_file_key = snapshot_rec['Key']
        tophash, snapshotpath = _parse_snapshot_path(snapshot_file_key)

        if prefix is None or prefix.startswith(snapshotpath):
            snapshotbytes, _ = download_bytes(f'{bucket}/{snapshot_file_key}')
            snapshot = json.loads(snapshotbytes.decode('utf-8'))
            message = snapshot.get('message')
            timestamp = snapshot_rec['LastModified']
            snapshots_list.append(dict(hash=tophash, path=snapshotpath, message=message, timestamp=timestamp))

    return snapshots_list


def create_snapshot(path, message):
    snapshot = {}
    obj_versions, _ = list_object_versions(path)
    for obj in obj_versions:
        key = obj['Key']
        etag = obj['ETag']
        vid = obj['VersionId']
        latest = bool(obj['IsLatest'])

        # Only check current object versions
        # Ignore snapshot files
        if latest and not key.startswith(SNAPSHOT_PREFIX):
            # make sure we only see one "Latest"
            assert key not in snapshot
            snapshot[key] = dict(
                Key = key,
                ETag = etag,
                VersionId = vid
                )

    bytes = json.dumps(dict(contents=snapshot, message=message, path=path), default=str).encode('utf-8')
    tophash = hashlib.sha256()
    tophash.update(bytes)
    tophash = tophash.hexdigest()

    upload_bytes(bytes, _snapshot_path(tophash, path), meta={})
    return tophash


def download_file_from_snapshot(src, dst, snapshothash):
    bucket, key = split_path(src)
    snapshot_data = read_snapshot_by_hash(bucket, snapshothash)
    obj_rec = snapshot_data['contents'][key]
    return download_file(src, dst, version=obj_rec['VersionId'])


def download_bytes_from_snapshot(src, snapshothash):
    bucket, key = split_path(src)
    snapshot_data = read_snapshot_by_hash(bucket, snapshothash)
    obj_rec = snapshot_data['contents'][key]
    return download_bytes(src, version=obj_rec['VersionId'])

class PhysicalKeyType(Enum):
    LOCAL = 'LOCAL'
    S3 = 'S3'

def hash_file(readable_file):
    """ Returns SHA256 hash of readable file-like object """
    buf = readable_file.read(4096)
    hasher = hashlib.sha256()
    while buf:
        hasher.update(buf)
        buf = readable_file.read(4096)

    return hasher.hexdigest()

def read_physical_key(physical_key):
    # TODO: Stream the data.
    url = urlparse(physical_key['path'])
    if url.scheme == 'file':
        with open(url2pathname(url.path), 'rb') as fd:
            return fd.read()
    elif url.scheme == 's3':
        version_id = _parse_version_id(url)
        return download_bytes(url.netloc + unquote(url.path), version_id)[0]
    else:
        raise NotImplementedError


def get_package_registry(path):
    """ Returns the package registry for a given path """
    if path.startswith('s3://'):
        bucket = path[5:].partition('/')[0]
        return "s3://{}/.quilt".format(bucket)
    else:
        raise NotImplementedError

def get_local_package_registry():    
    """ Returns a local package registry Path as a string. """
    Path(BASE_PATH, "packages").mkdir(parents=True, exist_ok=True)
    Path(BASE_PATH, "named_packages").mkdir(parents=True, exist_ok=True)
    return BASE_PATH

class PackageEntry(object):
    """
    Represents an entry at a logical key inside a package.
    """
    __slots__ = ['physical_keys', 'size', 'hash', 'meta']
    def __init__(self, physical_keys, size, hash_obj, meta):
        """
        Creates an entry.

        Args:
            physical_keys is a nonempty list of objects of the form {
                schema_version: string
                type: string
                uri: string
            }
            size(number): size of object in bytes
            hash({'type': string, 'value': string}): hash object
                for example: {'type': 'SHA256', 'value': 'bb08a...'}
            meta(dict): metadata dictionary

        Returns:
            a PackageEntry
        """
        assert physical_keys
        self.physical_keys = physical_keys
        self.size = size
        self.hash = hash_obj
        self.meta = meta

    def as_dict(self):
        """
        Returns dict representation of entry.
        """
        ret = {
            'physical_keys': self.physical_keys,
            'size': self.size,
            'hash': self.hash,
            'meta': self.meta
        }
        return copy.deepcopy(ret)

    @staticmethod
    def from_local_path(path):
        with open(path, 'rb') as file_to_hash:
            hash_obj = {
                'type': 'SHA256',
                'value': hash_file(file_to_hash)
            }

        size = os.path.getsize(path)
        physical_keys = [{
            'type': PhysicalKeyType.LOCAL.name,
            'path': pathlib.Path(path).resolve().as_uri()
        }]
        return PackageEntry(physical_keys, size, hash_obj, {})

    def _clone(self):
        """
        Returns clone of this package.
        """
        return PackageEntry(copy.deepcopy(self.physical_keys), self.size, \
                            copy.deepcopy(self.hash), copy.deepcopy(self.meta))

class Package(object):
    """ In-memory representation of a package """

    def __init__(self, data=None, meta=None):
        """
        _data is of the form {logical_key: PackageEntry}
        """
        self._data = data or {}
        self._meta = meta or {}

    def _clone(self):
        """
        Returns clone of this package.
        """
        return Package(copy.deepcopy(self._data), copy.deepcopy(self._meta))

    def __contains__(self, logical_key):
        """
        Checks whether the package contains a specified logical_key.

        Returns:
            True or False
        """
        return logical_key in self._data

    @staticmethod
    def load(readable_file):
        """
        Loads a package from a readable file-like object.

        Args:
            readable_file: readable file-like object to deserialize package from

        Returns:
            a new package object

        Raises:
            file not found
            json decode error
            invalid package exception
        """
        data = {}
        reader = jsonlines.Reader(readable_file)
        meta = reader.read()
        for obj in reader:
            lk = obj.pop('logical_key')
            if lk in data:
                raise PackageException("Duplicate logical key while loading package")
            data[lk] = PackageEntry(
                obj['physical_keys'],
                obj['size'],
                obj['hash'],
                obj['meta']
            )

        return Package(data, meta)

    @staticmethod
    def create_package(path):
        """
        Takes a package of a provided path.

        Recursively enumerates every file in path, and returns a new
        package that contains all those files.

        Args:
            path(string): path to package

        Returns:
            A new Package of that path

        Raises:
            when path doesn't exist
        """
        # TODO: anything but local paths
        # TODO: deserialization metadata
        data = {}
        meta = {'version': '0.0.1'}
        src_path = pathlib.Path(path)
        files = src_path.rglob('*')
        for f in files:
            if not f.is_file():
                continue

            entry = PackageEntry.from_local_path(f)
            logical_key = f.relative_to(src_path).as_posix()
            data[logical_key] = entry
        return Package(data, meta)

    def get(self, logical_key):
        """
        Gets object from local_key and returns it as an in-memory object.

        Args:
            logical_key(string): logical key of the object to get

        Returns:
            A tuple containing the deserialized object from the logical_key and its metadata

        Raises:
            KeyError: when logical_key is not present in the package
            physical key failure
            hash verification fail
            when deserialization metadata is not present
        """
        entry = self._data[logical_key]

        target_str = entry.meta.get('target')
        if target_str is None:
            raise HeliumException("No serialization metadata")

        try:
            target = TargetType(target_str)
        except ValueError:
            raise HeliumException("Unknown serialization target: %r" % target_str)

        physical_keys = entry.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys

        data = read_physical_key(physical_key)

        # TODO: verify hash

        return deserialize_obj(data, target), entry.meta.get('user_meta')

    def copy(self, logical_key, dest):
        """
        Gets objects from logical_key inside the package and saves them to dest.

        Args:
            logical_key: logical key inside package to get
            dest: where to put the files

        Returns:
            None

        Raises:
            logical key not found
            physical key failure
            fail to create file
            fail to finish write
        """
        entry = self._data[logical_key]

        physical_keys = entry.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys

        dest = _fix_url(dest)

        _copy_file(physical_key['path'], dest, entry.meta)

    def get_meta(self, logical_key):
        """
        Returns metadata for specified logical key.
        """
        entry = self._data[logical_key]
        return entry.meta

    def build(self, name=None):
        """
        Serializes this package to a local registry.

        Args:
            name: optional name for package in registry
                    defaults to the textual hash of the package manifest

        Returns:
            the top hash as a string
        """
        hash_string = self.top_hash()["value"]
        with open(get_local_package_registry() / "packages" / hash_string, "w") as fh:
            self.dump(fh)

        if name:
            # Build the package directory if necessary.
            named_path = get_local_package_registry() / "named_packages" / name
            named_path.mkdir(parents=True, exist_ok=True)
            # todo: use a float to string formater instead of double casting
            with open(named_path / str(int(time.time())), "w") as fh:
                fh.write(self.top_hash()["value"])
            # todo: symlink when local
            with open(named_path / "latest", "w") as fh:
                fh.write(self.top_hash()["value"])
        return hash_string

    def dump(self, writable_file):
        """
        Serializes this package to a writable file-like object.

        Args:
            writable_file: file-like object to write serialized package.

        Returns:
            None

        Raises:
            fail to create file
            fail to finish write
        """
        self.top_hash() # assure top hash is calculated
        writer = jsonlines.Writer(writable_file)
        writer.write(self._meta)
        for logical_key, entry in self._data.items():
            writer.write({'logical_key': logical_key, **entry.as_dict()})

    def set(self, logical_key, entry=None, meta=None):
        """
        Returns a new package with the object at logical_key set to entry.

        Args:
            logical_key(string): logical key to update
            entry(PackageEntry OR string): new entry to place at logical_key in the package
                if entry is a string, it is treated as a path to local disk and an entry
                is created based on the file at that path on your local disk
            meta(dict): metadata dict to attach to entry. If meta is provided, set just
                updates the meta attached to logical_key without changing anything
                else in the entry

        Returns:
            A new package
        """
        if entry is None and meta is None:
            raise PackageException('Must specify either entry or meta')

        if entry is None:
            return self._update_meta(logical_key, meta)

        pkg = self._clone()
        if isinstance(entry, str):
            entry = PackageEntry.from_local_path(entry)
            if meta is not None:
                entry.meta = meta
            pkg._data[logical_key] = entry
        elif isinstance(entry, PackageEntry):
            pkg._data[logical_key] = entry
            if meta is not None:
                raise PackageException("Must specify metadata in the entry")
        else:
            raise NotImplementedError
        return pkg

    def _update_meta(self, logical_key, meta):
        pkg = self._clone()
        pkg._data[logical_key].meta = meta
        return pkg

    def delete(self, logical_key):
        """
        Returns a new package with logical_key removed.

        Returns:
            A new package

        Raises:
            KeyError: when logical_key is not present to be deleted
        """
        pkg = self._clone()
        pkg._data.pop(logical_key)
        return pkg

    def _top_hash(self):
        """
        Sets the top_hash in _meta

        Returns:
            None
        """
        top_hash = hashlib.sha256()
        hashable_meta = copy.deepcopy(self._meta)
        hashable_meta.pop('top_hash', None)
        top_meta = json.dumps(hashable_meta, sort_keys=True, separators=(',', ':'))
        top_hash.update(top_meta.encode('utf-8'))
        for logical_key, entry in sorted(list(self._data.items())):
            entry_dict = entry.as_dict()
            entry_dict['logical_key'] = logical_key
            entry_dict.pop('physical_keys', None)
            entry_dict_str = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
            top_hash.update(entry_dict_str.encode('utf-8'))

        self._meta['top_hash'] = {
            'alg': 'v0',
            'value': top_hash.hexdigest()
        }

    def top_hash(self):
        """
        Returns the top hash of the package.

        Note that physical keys are not hashed because the package has
            the same semantics regardless of where the bytes come from.

        Returns:
            A string that represents the top hash of the package
        """
        if 'top_hash' not in self._meta:
            self._top_hash()
        return self._meta['top_hash']

    def push(self, name, path):
        """
        Copies objects to path, then creates a new package that points to those objects.
        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.
        Args:
            path: where to copy the objects in the package
            name: name for package in registry
        Returns:
            A new package that points to the copied objects
        """
        if not path.startswith('s3://'):
            raise NotImplementedError
        if not name:
            # todo: handle where to put data for unnamed remote packages
            raise NotImplementedError
        pkg = self._materialize('{}/{}'.format(path.strip("/"), name))

        with tempfile.NamedTemporaryFile() as manifest:
            pkg.dump(manifest)
            manifest.flush()
            _copy_file(
                pathlib.Path(manifest.name).resolve().as_uri(),
                get_package_registry(path) + "/packages/" + pkg.top_hash()["value"],
                {}
            )

        if name:
            # Build the package directory if necessary.
            named_path = get_package_registry(path) + '/named_packages/' + name + "/"
            # todo: use a float to string formater instead of double casting
            with tempfile.NamedTemporaryFile() as hash_file:
                hash_file.write(pkg.top_hash()["value"].encode('utf-8'))
                hash_file.flush()
                _copy_file(
                    pathlib.Path(hash_file.name).resolve().as_uri(),
                    named_path + str(int(time.time())),
                    {}
                )
                hash_file.seek(0)
                _copy_file(
                    pathlib.Path(hash_file.name).resolve().as_uri(),
                    named_path + "latest",
                    {}
                )
        return pkg

    def _materialize(self, path):
        """
        Copies objects to path, then creates a new package that points to those objects.

        Copies each object in this package to path according to logical key structure,
        and returns a package with physical_keys that point to the new copies.

        Args:
            path: where to copy the objects in the package

        Returns:
            A new package that points to the copied objects

        Raises:
            fail to get bytes
            fail to put bytes
            fail to put package to registry
        """
        pkg = self._clone()
        for logical_key, entry in self._data.items():
            # Copy the datafiles in the package.
            if path.startswith('s3://'):
                new_physical_key = path + "/" + logical_key
                new_type = PhysicalKeyType.S3.name
            else:
                new_physical_key = os.path.join(path, logical_key).resolve().as_uri()
                new_type = PhysicalKeyType.LOCAL.name

            self.copy(logical_key, new_physical_key)
            # Create a new package pointing to the new remote key.
            new_entry = entry._clone()
            new_entry.physical_keys = [{
                'type': new_type,
                'path': new_physical_key
            }]
            # Treat as a local path
            pkg = pkg.set(logical_key, new_entry)
        return pkg
