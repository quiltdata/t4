import boto3
import hashlib
import json

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


def get_snapshots(path):
    bucket, prefix = split_path(path)
    snapshot_files = list_objects(f'{bucket}/{SNAPSHOT_PREFIX}')

    snapshots_list = []
    for snapshot_rec in sorted(snapshot_files, key=lambda k: k['LastModified'], reverse=True):
        snapshot_file_key = snapshot_rec['Key']
        tophash, snapshotpath = _parse_snapshot_path(snapshot_file_key)
        
        if prefix.startswith(snapshotpath):
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
