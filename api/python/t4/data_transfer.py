from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import hashlib
import json
import pathlib
import platform
import shutil
from threading import Lock
from urllib.parse import urlparse

from botocore.exceptions import ClientError
import boto3
from boto3.s3.transfer import TransferConfig, create_transfer_manager
from s3transfer.subscribers import BaseSubscriber
from six import BytesIO, binary_type, text_type
from tqdm.autonotebook import tqdm

from .util import HeliumException, split_path, parse_file_url, parse_s3_url
from . import xattr


HELIUM_METADATA = 'helium'
HELIUM_XATTR = 'com.quiltdata.helium'
EXTENSION_TARGET_MAP = {
    'bin': 'bytes',
    'json': 'json',
    'md': 'unicode',
    'npy': 'numpy',
    'npz': 'numpy',
    'parquet': 'pyarrow',
    'rst': 'unicode',
    'txt': 'unicode',
    }


if platform.system() == 'Linux':
    # Linux only allows users to modify user.* xattrs.
    HELIUM_XATTR = 'user.%s' % HELIUM_XATTR

s3_client = boto3.client('s3')
s3_transfer_config = TransferConfig()
s3_manager = create_transfer_manager(s3_client, s3_transfer_config)

# s3transfer does not give us a way to access the metadata of an object it's downloading,
# even though it has access to it. To get around this, we patch the s3 client to get a callback
# with the response.
# See https://github.com/boto/s3transfer/issues/104
_old_get_object = s3_client.get_object
def _get_object(self, **kwargs):
    callback = kwargs.pop('Callback', None)
    resp = _old_get_object(**kwargs)
    if callback is not None:
        callback(resp)
    return resp
s3_client.get_object = type(_old_get_object)(_get_object, s3_client)

s3_manager.ALLOWED_DOWNLOAD_ARGS = s3_manager.ALLOWED_DOWNLOAD_ARGS + ['Callback']


class TargetType(Enum):
    """
    Enums for target types
    """
    BYTES = 'bytes'
    UNICODE = 'unicode'
    JSON = 'json'
    PYARROW = 'pyarrow'
    NUMPY = 'numpy'


for value in EXTENSION_TARGET_MAP.values():
    TargetType(value)  # EXTENSION_TARGET_MAP values must be present in TargetType


def deserialize_obj(data, target):
    if target == TargetType.BYTES:
        obj = data
    elif target == TargetType.UNICODE:
        obj = data.decode('utf-8')
    elif target == TargetType.JSON:
        obj = json.loads(data.decode('utf-8'))
    elif target == TargetType.NUMPY:
        import numpy as np
        buf = BytesIO(data)
        obj = np.load(buf, allow_pickle=False)
    elif target == TargetType.PYARROW:
        import pyarrow as pa
        from pyarrow import parquet
        buf = BytesIO(data)
        table = parquet.read_table(buf)
        try:
            obj = pa.Table.to_pandas(table)
        except AssertionError:
            # Try again to convert the table after removing
            # the possibly buggy Pandas-specific metadata.
            meta = table.schema.metadata.copy()
            meta.pop(b'pandas')
            newtable = table.replace_schema_metadata(meta)
            obj = newtable.to_pandas()
    else:
        raise NotImplementedError

    return obj


def _guess_target_by_ext(name, default='bytes'):
    ### This *should* match get_target_for_obj as much as possible.
    if default is not None:
        TargetType(default)  # ..must exist as a TargetType
    if '.' not in name:
        return default
    ext = name.rsplit('.', 1)[1].lower()
    return EXTENSION_TARGET_MAP.get(ext, default)


def _get_target_for_object(obj):
    # TODO: Lazy loading.
    import numpy as np
    import pandas as pd

    if isinstance(obj, binary_type):
        target = TargetType.BYTES
    elif isinstance(obj, text_type):
        target = TargetType.UNICODE
    elif isinstance(obj, dict):
        target = TargetType.JSON
    elif isinstance(obj, np.ndarray):
        target = TargetType.NUMPY
    elif isinstance(obj, pd.DataFrame):
        target = TargetType.PYARROW
    else:
        raise HeliumException("Unsupported object type")
    return target

def serialize_obj(obj):
    target = _get_target_for_object(obj)

    if target == TargetType.BYTES:
        data = obj
    elif target == TargetType.UNICODE:
        data = obj.encode('utf-8')
    elif target == TargetType.JSON:
        data = json.dumps(obj).encode('utf-8')
    elif target == TargetType.NUMPY:
        import numpy as np
        buf = BytesIO()
        np.save(buf, obj, allow_pickle=False)
        data = buf.getvalue()
    elif target == TargetType.PYARROW:
        import pyarrow as pa
        from pyarrow import parquet
        buf = BytesIO()
        table = pa.Table.from_pandas(obj)
        parquet.write_table(table, buf)
        data = buf.getvalue()
    else:
        raise HeliumException("Don't know how to serialize object")

    return data, target


class SizeCallback(BaseSubscriber):
    def __init__(self, size):
        self.size = size

    def on_queued(self, future, **kwargs):
        future.meta.provide_transfer_size(self.size)


class ProgressCallback(BaseSubscriber):
    def __init__(self, progress):
        self._progress = progress
        self._lock = Lock()

    def on_progress(self, future, bytes_transferred, **kwargs):
        with self._lock:
            self._progress.update(bytes_transferred)


def _parse_metadata(resp):
    return json.loads(resp['Metadata'].get(HELIUM_METADATA, '{}'))


def _response_generator(func, tokens, kwargs):
    while True:
        response = func(**kwargs)
        yield response
        if not response['IsTruncated']:
            break
        for token in tokens:
            kwargs[token] = response['Next' + token]


def _list_objects(**kwargs):
    return _response_generator(s3_client.list_objects_v2, ['ContinuationToken'], kwargs)


def _list_object_versions(**kwargs):
    return _response_generator(s3_client.list_object_versions, ['KeyMarker', 'VersionIdMarker'], kwargs)


def _download_single_file(bucket, key, dest_path, version=None):
    params = dict(Bucket=bucket, Key=key)
    if version is not None:
        params.update(dict(VersionId=version))
    resp = s3_client.head_object(**params)
    size = resp['ContentLength']
    meta = _parse_metadata(resp)
    extra = dict(VersionId=version) if version is not None else {}

    if dest_path.endswith('/'):
        dest_path += pathlib.PurePosixPath(key).name

    if pathlib.Path(dest_path).is_reserved():
        raise ValueError("Cannot download %r: reserved file name" % dest_path)

    with tqdm(total=size, unit='B', unit_scale=True) as progress:
        future = s3_manager.download(
            bucket, key, dest_path, subscribers=[SizeCallback(size), ProgressCallback(progress)],
            extra_args=extra
        )
        future.result()
        xattr.setxattr(dest_path, HELIUM_XATTR, json.dumps(meta).encode('utf-8'))


def _download_dir(bucket, prefix, dest_path):
    if not dest_path.endswith('/'):
        raise ValueError("Destination path must end in /")

    dest_dir = pathlib.Path(dest_path)

    total_size = 0
    tuples_list = []

    for resp in _list_objects(Bucket=bucket, Prefix=prefix):
        for item in resp.get('Contents', []):
            key = item['Key']
            size = item['Size']
            total_size += size

            rel_key = key[len(prefix):]
            dest_file = dest_dir / rel_key

            # Make sure it doesn't contain '..' or anything like that
            try:
                dest_file.resolve().relative_to(dest_dir.resolve())
            except ValueError:
                raise ValueError("Cannot download %r: outside of destination directory" % dest_file)

            if dest_file.is_reserved():
                raise ValueError("Cannot download %r: reserved file name" % dest_file)

            tuples_list.append((key, dest_file, size))

    with tqdm(total=total_size, unit='B', unit_scale=True) as progress:
        callback = ProgressCallback(progress)

        metadata = {}
        lock = Lock()

        futures = []
        for key, dest_file, size in tuples_list:
            def meta_callback(resp):
                meta = _parse_metadata(resp)
                with lock:
                    metadata[key] = meta
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            future = s3_manager.download(
                bucket, key, str(dest_file),
                extra_args=dict(Callback=meta_callback), subscribers=[SizeCallback(size), callback]
            )
            futures.append(future)

        for future in futures:
            future.result()

        for key, dest_file, _ in tuples_list:
            meta = metadata[key]
            xattr.setxattr(dest_file, HELIUM_XATTR, json.dumps(meta).encode('utf-8'))


def download_file(src_path, dest_path, version=None):
    bucket, key = split_path(src_path)

    if src_path.endswith('/'):
        if version is not None:
            raise HeliumException("Cannot specify a Version ID for a directory.")
        _download_dir(bucket, key, dest_path)
    else:
        _download_single_file(bucket, key, dest_path, version=version)


def download_bytes(path, version=None):
    bucket, key = split_path(path, require_subpath=True)
    params = dict(Bucket=bucket,
                  Key=key)
    if version is not None:
        params.update(dict(VersionId=version))

    resp = s3_client.get_object(**params)
    meta = _parse_metadata(resp)
    body = resp['Body'].read()
    return body, meta


def _calculate_etag(file_obj):
    """
    Attempts to calculate a local file's ETag the way S3 does:
    - Normal uploads: MD5 of the file
    - Multi-part uploads: MD5 of the (binary) MD5s of the parts, dash, number of parts
    We can't know how the file was actually uploaded - but we're assuming it was done using
    the default settings, which we get from `s3_transfer_config`.
    """
    size = file_obj.stat().st_size
    with open(file_obj, 'rb') as fd:
        if size <= s3_transfer_config.multipart_threshold:
            contents = fd.read()
            etag = hashlib.md5(contents).hexdigest()
        else:
            hashes = []
            while True:
                contents = fd.read(s3_transfer_config.multipart_chunksize)
                if not contents:
                    break
                hashes.append(hashlib.md5(contents).digest())
            etag = '%s-%d' % (hashlib.md5(b''.join(hashes)).hexdigest(), len(hashes))
    return '"%s"' % etag


def upload_file(src_path, dest_path, override_meta=None):
    src_file = pathlib.Path(src_path)
    is_dir = src_file.is_dir()
    if src_path.endswith('/'):
        if not is_dir:
            raise ValueError("Source path not a directory")
        if not dest_path.endswith('/'):
            raise ValueError("Destination path must end in /")
    else:
        if is_dir:
            raise ValueError("Source path is a directory; must end in /")

    if is_dir:
        src_root = src_file
        src_file_list = list(f for f in src_file.rglob('*') if f.is_file())
    else:
        src_root = src_file.parent
        src_file_list = [src_file]

    bucket, key = split_path(dest_path)

    total_size = sum(f.stat().st_size for f in src_file_list)

    with ThreadPoolExecutor() as executor:
        # Calculate local ETags in parallel.
        src_etag_iter = executor.map(_calculate_etag, src_file_list)

        # While waiting for the above, get ETags for the destination dir in the bucket.
        # (Listing the whole bucket is slow, but the target dir might be a good compromise.)
        existing_etags = {}
        for response in _list_object_versions(Bucket=bucket, Prefix=key):
            for obj in response.get('Versions', []):
                existing_etags[obj['ETag']] = (obj['Key'], obj['VersionId'])

        src_etag_list = list(src_etag_iter)

    with tqdm(total=total_size, unit='B', unit_scale=True) as progress:
        callback = ProgressCallback(progress)

        futures = []
        for f, etag in zip(src_file_list, src_etag_list):
            real_dest_path = key + str(f.relative_to(src_root)) if (not key or key.endswith('/')) else key

            if override_meta is None:
                try:
                    meta_bytes = xattr.getxattr(f, HELIUM_XATTR)
                    meta = json.loads(meta_bytes.decode('utf-8'))
                except IOError:
                    # No metadata
                    meta = {}
                except ValueError:
                    raise ValueError("Source path contains invalid metadata")
            else:
                meta = override_meta

            extra_args = dict(Metadata={HELIUM_METADATA: json.dumps(meta)})
            existing_src = existing_etags.get(etag)
            if existing_src is not None:
                # We found an existing object with the same ETag, so copy it instead of uploading
                # the bytes. (In the common case, it's the same key - the object is already there -
                # but we still copy it onto itself just in case the metadata has changed.)
                future = s3_manager.copy(
                    dict(Bucket=bucket, Key=existing_src[0], VersionId=existing_src[1]),
                    bucket, real_dest_path, extra_args, [callback]
                )
            else:
                # Upload the file.
                future = s3_manager.upload(str(f), bucket, real_dest_path, extra_args, [callback])
            futures.append(future)

        for future in futures:
            future.result()


def upload_bytes(data, path, meta):
    bucket, key = split_path(path, require_subpath=True)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
        Metadata={HELIUM_METADATA: json.dumps(meta)}
    )


def delete_object(path):
    bucket, key = split_path(path, require_subpath=True)

    if path.endswith('/'):
        for response in _list_objects(Bucket=bucket, Prefix=key):
            for obj in response.get('Contents', []):
                s3_client.delete_object(Bucket=bucket, Key=obj['Key'])
    else:
        s3_client.head_object(Bucket=bucket, Key=key)  # Make sure it exists
        s3_client.delete_object(Bucket=bucket, Key=key)  # Actually delete it

NO_OP_COPY_ERROR_MESSAGE = ("An error occurred (InvalidRequest) when calling "
                            "the CopyObject operation: This copy request is illegal "
                            "because it is trying to copy an object to itself "
                            "without changing the object's metadata, storage "
                            "class, website redirect location or encryption "
                            "attributes.")

def copy_object(src, dest, override_meta=None, version=None):
    src_bucket, src_key = split_path(src, require_subpath=True)
    dest_bucket, dest_key = split_path(dest, require_subpath=True)
    src_params = dict(
        Bucket=src_bucket,
        Key=src_key
    )
    if version is not None:
        src_params.update(
            VersionId=version
        )

    params = dict(
        CopySource=src_params,
        Bucket=dest_bucket,
        Key=dest_key
    )
    if override_meta is None:
        params.update(dict(
            MetadataDirective='COPY'
        ))
    else:
        params.update(dict(
            MetadataDirective='REPLACE',
            Metadata={HELIUM_METADATA: json.dumps(override_meta)}
        ))

    try:
        s3_client.copy_object(**params)
    except ClientError as e:
        # suppress error from copying a file to itself
        if str(e) == NO_OP_COPY_ERROR_MESSAGE:
            return
        raise


def list_object_versions(path, recursive=True):
    bucket, key = split_path(path)
    list_obj_params = dict(Bucket=bucket,
                           Prefix=key
                          )
    if not recursive:
        # Treat '/' as a directory separator and only return one level of files instead of everything.
        list_obj_params.update(dict(Delimiter='/'))

    # TODO: make this a generator?
    versions = []
    delete_markers = []
    prefixes = []

    for response in _list_object_versions(**list_obj_params):
        versions += response.get('Versions', [])
        delete_markers += response.get('DeleteMarkers', [])
        prefixes += response.get('CommonPrefixes', [])

    if recursive:
        return versions, delete_markers
    else:
        return prefixes, versions, delete_markers


def list_objects(path, recursive=True):
    bucket, prefix = split_path(path)
    objects = []
    prefixes = []
    list_obj_params = dict(Bucket=bucket,
                           Prefix=prefix)
    if not recursive:
        # Treat '/' as a directory separator and only return one level of files instead of everything.
        list_obj_params.update(dict(Delimiter='/'))

    for response in _list_objects(**list_obj_params):
        objects += response.get('Contents', [])
        prefixes += response.get('CommonPrefixes', [])

    if recursive:
        return objects
    else:
        return prefixes, objects


def copy_file(src, dest, override_meta=None):
    src_url = urlparse(src)
    dest_url = urlparse(dest)
    if src_url.scheme == 'file':
        if dest_url.scheme == 'file':
            # TODO: metadata
            shutil.copyfile(parse_file_url(src_url), parse_file_url(dest_url))
        elif dest_url.scheme == 's3':
            dest_bucket, dest_path, dest_version_id = parse_s3_url(dest_url)
            if dest_version_id:
                raise ValueError("Cannot set VersionId on destination")
            upload_file(parse_file_url(src_url), dest_bucket + '/' + dest_path, override_meta)
        else:
            raise NotImplementedError
    elif src_url.scheme == 's3':
        src_bucket, src_path, src_version_id = parse_s3_url(src_url)
        if dest_url.scheme == 'file':
            # TODO: metadata
            download_file(src_bucket + '/' + src_path, parse_file_url(dest_url), src_version_id)
        elif dest_url.scheme == 's3':
            dest_bucket, dest_path, dest_version_id = parse_s3_url(dest_url)
            if dest_version_id:
                raise ValueError("Cannot set VersionId on destination")
            copy_object(src_bucket + '/' + src_path, dest_bucket + '/' + dest_path, override_meta, src_version_id)
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError
