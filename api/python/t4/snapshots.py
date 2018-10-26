import copy
from enum import Enum
import hashlib
import json
import pathlib
import os

import boto3
import jsonlines

from .data_transfer import (download_bytes, download_file, list_objects,
                            list_object_versions, upload_bytes)
from .exceptions import PackageException
from .util import HeliumException, split_path

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
    LOCAL = 1
    S3 = 2

def hash_file(readable_file):
    """ Returns SHA256 hash of readable file-like object """
    buf = readable_file.read(4096)
    hasher = hashlib.sha256()
    while buf:
        hasher.update(buf)
        buf = readable_file.read(4096)

    return hasher.hexdigest()

def dereference_physical_key(physical_key):
    ty = physical_key['type']
    if ty == PhysicalKeyType.LOCAL.name:
        return open(physical_key['path'])

    raise NotImplementedError

def get_package_registry_root(path=''):
    """ Returns the package registry root for a given path """
    if path.startswith('s3://'):
        bucket = path[5:].partition('/')[0]
        return "s3://{}".format(bucket)
    else:
        # TODO: return local registry root
        raise NotImplementedError

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

class Package(object):
    """ In-memory representation of a package """

    def __init__(self, name=None, pkg_hash=None, registry=None):
        """
        Create a Package from scratch, or load one from a registry.

        Args:
            name(string): name of package to load
            pkg_hash(string): top hash of package version to load
            registry(string): location of registry to load package from
        """
        if name is None and pkg_hash is None and registry is None:
            self._data = {}
            self._meta = {'version': 'v0'}
            return

        if registry is None:
            # default to local registry
            registry = get_package_registry_root()

        if pkg_hash is not None:
            # if hash is specified, name doesn't matter
            pkg_path = registry + '/packages/{}'.format(pkg_hash)
            # TODO replace open with something that supports both local and s3
            with open(pkg_path) as pkg_file:
                pkg = self.load(pkg_file)
            self = pkg._clone()

        pkg_path = registry + '/named_packages/{}/'.format(name)
        # TODO: list files at this directory
        # TODO: default to latest version of named package
        raise NotImplementedError

    def _set_state(self, data, meta):
        self._data = data
        self._meta = meta
        return self

    def _clone(self):
        """
        Returns clone of this package.
        """
        return Package()._set_state(copy.deepcopy(self._data), copy.deepcopy(self._meta))

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

        return Package()._set_state(data, meta)

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
        meta = {}
        src_path = pathlib.Path(path)
        files = src_path.rglob('*')
        for f in files:
            if not f.is_file():
                continue

            with open(f, 'rb') as file_to_hash:
                hash_obj = {
                    'type': 'SHA256',
                    'value': hash_file(file_to_hash)
                }

            size = os.path.getsize(f)
            physical_keys = [{
                'type': PhysicalKeyType.LOCAL.name,
                'path': os.path.abspath(f)
            }]
            entry = PackageEntry(physical_keys, size, hash_obj, {})
            logical_key = pathlib.Path(f).relative_to(src_path).as_posix()
            data[logical_key] = entry
        return Package()._set_state(data, meta)

    def get(self, logical_key):
        """
        Gets object from local_key and returns it as an in-memory object.

        Args:
            logical_key(string): logical key of the object to get

        Returns:
            A deserialized object from the logical_key

        Raises:
            KeyError: when logical_key is not present in the package
            physical key failure
            hash verification fail
            when deserialization metadata is not present
        """
        entry = self._data[logical_key]
        physical_keys = entry.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys
        # TODO: verify hash
        if 'target' in entry.meta:
            # TODO: dispatch on target to deserialize
            raise NotImplementedError

        raise NotImplementedError

    def get_files(self, logical_key, path):
        """
        Gets objects from logical_key inside the package and saves them to path.

        Args:
            logical_key: logical key inside package to get
            path: where to put the files

        Returns:
            None

        Raises:
            logical key not found
            physical key failure
            fail to create file
            fail to finish write
        """
        raise NotImplementedError

    def get_meta(self, logical_key):
        """
        Returns user metadata for specified logical key.
        """
        entry = self._data[logical_key]
        return entry['user_meta']

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
        writer = jsonlines.Writer(writable_file)
        writer.write(self._meta)
        for logical_key, entry in self._data.items():
            writer.write({'logical_key': logical_key, **entry.as_dict()})

    def update(self, logical_key, entry):
        """
        Returns a new package with the object at logical_key set to entry.

        Args:
            logical_key(string): logical key to update
            entry(PackageEntry): new entry to place at logical_key in the package

        Returns:
            A new package
        """
        pkg = self._clone()
        # TODO validate entry contents
        pkg._data[logical_key] = entry
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
        raise NotImplementedError

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

    def materialize(self, path, name=None):
        """
        Copies objects to path, then creates a new package that points to those objects.

        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.

        Args:
            path: where to copy the objects in the package
            name: optional name for package in registry
                    defaults to the textual hash of the package manifest

        Returns:
            A new package that points to the copied objects

        Raises:
            fail to get bytes
            fail to put bytes
            fail to put package to registry
        """
        raise NotImplementedError
        if name is None:
            raise NotImplementedError
        self.get_files(path)
        self.dump(get_package_registry_root(path) + name)
