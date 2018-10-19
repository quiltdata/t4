import copy
import hashlib
import json
import pathlib
import os

import boto3
import jsonlines

from .data_transfer import (download_bytes, download_file, list_objects,
                            list_object_versions, upload_bytes)
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

def hash_file(path):
    """ Returns SHA256 hash of file at path. """
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

class PackageException(Exception):
    """ Exception relating to package validity. """
    pass


def dereference_physical_key(physical_key):
    ty = physical_key['type']
    if ty == 'local_file':
        return open(physical_key['path'])

    raise NotImplementedError


class Package(object):
    """ In-memory representation of a package """

    def __init__(self, data=None, meta=None):
        """
        _data is of the form {logical_key: entry}
        entry is of the form (physical_key, hash, size, user_meta)
        physical_keys is a list of objects of the form {
            schema_version: string
            type: string
            uri: string
        }
        hash is of the form {
            type: string (e.g. "SHA256")
            value: string
        }
        size is the length of the object in bytes
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
    def load(path):
        """
        Loads a package from a path.

        Args:
            path: string representing the location to load the package from

        Returns:
            a new package object

        Raises:
            file not found
            json decode error
            invalid package exception
        """
        data = {}
        with jsonlines.open(path) as reader:
            meta = reader.read()
            for obj in reader:
                lk = obj['logical_key']
                if lk in data:
                    raise PackageException("Duplicate logical key while loading package")
                del obj['logical_key']
                data[lk] = obj

        return Package(data, meta)

    @staticmethod
    def pkg(path):
        """
        Takes a package of a provided path.

        Recursively enumerates every file in path, and returns a new
        package that contains all those files.

        Args:
            path: path to package

        Returns:
            A new package of that path

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
            entry = {
                'hash': hash_file(f),
                'size': os.path.getsize(f),
                'user_meta': {},
                'physical_keys': [{
                    'type': 'local_file',
                    'path': os.path.abspath(f)
                }]
            }
            data[str(f)] = entry
        return Package(data, meta)

    def get(self, logical_key):
        """
        Gets object from local_key and returns it as an in-memory object.

        Args:
            logical_key: logical key of the object to get

        Returns:
            A deserialized object from the logical_key or
                a stream of bytes if deserialization info is missing

        Raises:
            KeyError: when logical_key is not present in the package
            physical key failure
            hash verification fail
        """
        entry = self._data[logical_key]
        physical_keys = entry['physical_keys']
        physical_key = physical_keys[0] # TODO: support multiple physical keys
        stream = dereference_physical_key(physical_key)
        # TODO: verify hash
        if 'target' in entry:
            # TODO: dispatch on target to deserialize
            raise NotImplementedError

        return stream

    def get_file(self, logical_key, path):
        """
        Gets object from logical_key inside the package and saves it to path.

        Args:
            logical_key: logical key inside package to get
            path: where to put the file

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

    def dump(self, path):
        """
        Serializes this package to a file at path.

        Args:
            path: where to serialize the package to

        Returns:
            None

        Raises:
            fail to create file
            fail to finish write
        """
        with open(path, mode='w') as f:
            with jsonlines.Writer(f) as writer:
                writer.write(self._meta)
                for logical_key, obj in self._data.items():
                    obj['logical_key'] = logical_key
                    writer.write(obj)

    def update(self, logical_key, entry):
        """
        Returns a new package with the object at logical_key set to entry.

        Args:
            logical_key: logical key to update
            entry: new entry to place at logical_key in the package

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

    def top_hash(self):
        """
        Returns the top hash of the package.

        Note that physical keys are not hashed because the package has
            the same semantics regardless of where the bytes come from.

        Returns:
            A string that represents the top hash of the package
        """
        raise NotImplementedError

    def materialize(self, path):
        """
        Copies objects to path, then creates a new package that points to those objects.

        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.

        Args:
            path: where to copy the objects in the package

        Returns:
            A new package that points to the copied objects

        Raises:
            fail to get bytes
            fail to put bytes
            fail to put package to registry
        """
        raise NotImplementedError
