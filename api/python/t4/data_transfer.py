from codecs import iterdecode
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import hashlib
import json
import pathlib
import platform
import shutil
from threading import Lock
from urllib.parse import urlparse

from botocore import UNSIGNED
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError
import boto3
from boto3.s3.transfer import TransferConfig, create_transfer_manager
from s3transfer.subscribers import BaseSubscriber
from six import BytesIO, binary_type, text_type
from urllib.parse import quote

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from tqdm.autonotebook import tqdm

import jsonlines

from .util import QuiltException, parse_file_url, parse_s3_url
from . import xattr


HELIUM_METADATA = 'helium'
HELIUM_XATTR = 'com.quiltdata.helium'

if platform.system() == 'Linux':
    # Linux only allows users to modify user.* xattrs.
    HELIUM_XATTR = 'user.%s' % HELIUM_XATTR

s3_client = boto3.client('s3')
try:
    # Ensure that user has AWS credentials that function.
    # quilt-example is readable by anonymous users, if the head fails
    #   then the s3 client needs to be in UNSIGNED mode
    #   because the user's credentials aren't working
    s3_client.head_bucket(Bucket='quilt-example')
except (ClientError, NoCredentialsError):
    # Use unsigned boto if credentials can't head the default bucket
    s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))

s3_transfer_config = TransferConfig()
s3_manager = create_transfer_manager(s3_client, s3_transfer_config)

# s3transfer does not give us a way to access the metadata of an object it's uploading/downloading,
# even though it has access to it. To get around this, we patch the s3 client to get a callback
# with the response.
# See https://github.com/boto/s3transfer/issues/104

def _add_callback(method):
    def wrapper(self, **kwargs):
        callback = kwargs.pop('Callback', None)
        resp = method(**kwargs)
        if callback is not None:
            callback(resp)
        return resp
    return type(method)(wrapper, method.__self__)

for name in ['get_object', 'put_object', 'copy_object']:
    orig_method = getattr(s3_client, name)
    new_method = _add_callback(orig_method)
    setattr(s3_client, name, new_method)

s3_manager.ALLOWED_DOWNLOAD_ARGS = s3_manager.ALLOWED_DOWNLOAD_ARGS + ['Callback']
s3_manager.ALLOWED_UPLOAD_ARGS = s3_manager.ALLOWED_UPLOAD_ARGS + ['Callback']
s3_manager.ALLOWED_COPY_ARGS = s3_manager.ALLOWED_COPY_ARGS + ['Callback']


class TargetType(Enum):
    """
    Enums for target types
    """
    BYTES = 'bytes'
    UNICODE = 'unicode'
    JSON = 'json'
    PYARROW = 'pyarrow'
    NUMPY = 'numpy'


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
        raise QuiltException("Unsupported object type")
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
        raise QuiltException("Don't know how to serialize object")

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

def _parse_file_metadata(path):
    try:
        meta_bytes = xattr.getxattr(path, HELIUM_XATTR)
        meta = json.loads(meta_bytes.decode('utf-8'))
    except IOError:
        # No metadata
        meta = {}
    return meta

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

    if not tuples_list:
        raise QuiltException("No objects to download.")

    with tqdm(total=total_size, unit='B', unit_scale=True) as progress:
        callback = ProgressCallback(progress)

        metadata = {}
        lock = Lock()

        futures = []
        for key, dest_file, size in tuples_list:
            def meta_callback(key):
                def cb(resp):
                    meta = _parse_metadata(resp)
                    with lock:
                        metadata[key] = meta
                return cb
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            future = s3_manager.download(
                bucket, key, str(dest_file),
                extra_args=dict(Callback=meta_callback(key)), subscribers=[SizeCallback(size), callback]
            )
            futures.append(future)

        for future in futures:
            future.result()

        for key, dest_file, _ in tuples_list:
            meta = metadata[key]
            xattr.setxattr(dest_file, HELIUM_XATTR, json.dumps(meta).encode('utf-8'))


def download_file(bucket, key, dest_path, version=None):
    if key.endswith('/'):
        if version is not None:
            raise QuiltException("Cannot specify a Version ID for a directory.")
        _download_dir(bucket, key, dest_path)
    else:
        _download_single_file(bucket, key, dest_path, version=version)


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


def upload_file(src_path, bucket, key, override_meta=None):
    src_file = pathlib.Path(src_path)
    is_dir = src_file.is_dir()
    if src_path.endswith('/'):
        if not is_dir:
            raise ValueError("Source path not a directory")
        if not key.endswith('/'):
            raise ValueError("Destination path must end in /")
    else:
        if is_dir:
            raise ValueError("Source path is a directory; must end in /")

    if is_dir:
        src_root = src_file
        src_file_list = list(f for f in src_file.rglob('*') if f.is_file())
        versioned_key = None
    else:
        src_root = src_file.parent
        src_file_list = [src_file]
        versioned_key = [None]

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
                meta = _parse_file_metadata(f)
            else:
                meta = override_meta

            def meta_callback(bucket, real_dest_path, versioned_key):
                def cb(resp):
                    version_id = resp.get('VersionId', 'null')  # Absent in unversioned buckets.
                    if versioned_key is not None:
                        obj_url = 's3://%s/%s' % (bucket, real_dest_path)
                        if version_id != 'null':  # Yes, 'null'
                            obj_url += '?versionId=%s' % quote(version_id)
                        versioned_key[0] = obj_url
                return cb

            extra_args = dict(Metadata={HELIUM_METADATA: json.dumps(meta)},
                              Callback=meta_callback(bucket, real_dest_path, versioned_key))
            existing_src = existing_etags.get(etag)
            if existing_src is not None:
                # We found an existing object with the same ETag, so copy it instead of uploading
                # the bytes. (In the common case, it's the same key - the object is already there -
                # but we still copy it onto itself just in case the metadata has changed.)
                extra_args['MetadataDirective'] = 'REPLACE'
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
    return versioned_key

def delete_object(bucket, key):
    if key.endswith('/'):
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

def copy_object(src_bucket, src_key, dest_bucket, dest_key, override_meta=None, version=None):
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
        resp = s3_client.copy_object(**params)
        version_id = resp.get('VersionId', 'null')  # Absent in unversioned buckets.
        obj_url = 's3://%s/%s' % (dest_bucket, dest_key)
        if version_id != 'null':  # Yes, 'null'
            obj_url += '?versionId=%s' % quote(version_id)
        return [obj_url]
    except ClientError as e:
        # suppress error from copying a file to itself
        if str(e) == NO_OP_COPY_ERROR_MESSAGE:
            return
        raise


def list_object_versions(bucket, prefix, recursive=True):
    if prefix and not prefix.endswith('/'):
        raise ValueError("Prefix must end with /")

    list_obj_params = dict(Bucket=bucket,
                           Prefix=prefix
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


def list_objects(bucket, prefix, recursive=True):
    if prefix and not prefix.endswith('/'):
        raise ValueError("Prefix must end with /")

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
            src_path = parse_file_url(src_url)
            dest_path = parse_file_url(dest_url)
            pathlib.Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src_path, dest_path)
            shutil.copymode(src_path, dest_path)
            try:
                meta_bytes = xattr.getxattr(src_path, HELIUM_XATTR)
            except IOError:
                # No metadata
                pass
            else:
                xattr.setxattr(dest_path, HELIUM_XATTR, meta_bytes)
        elif dest_url.scheme == 's3':
            dest_bucket, dest_path, dest_version_id = parse_s3_url(dest_url)
            if dest_version_id:
                raise ValueError("Cannot set VersionId on destination")
            return upload_file(parse_file_url(src_url), dest_bucket, dest_path, override_meta)
        else:
            raise NotImplementedError
    elif src_url.scheme == 's3':
        src_bucket, src_path, src_version_id = parse_s3_url(src_url)
        if dest_url.scheme == 'file':
            pathlib.Path(parse_file_url(dest_url)).parent.mkdir(parents=True, exist_ok=True)
            download_file(src_bucket, src_path, parse_file_url(dest_url), src_version_id)
        elif dest_url.scheme == 's3':
            dest_bucket, dest_path, dest_version_id = parse_s3_url(dest_url)
            if dest_version_id:
                raise ValueError("Cannot set VersionId on destination")
            return copy_object(src_bucket, src_path, dest_bucket, dest_path, override_meta,
                               src_version_id)
        else:
            raise NotImplementedError
    else:
        raise NotImplementedError

def put_bytes(data, dest, meta=None):
    dest_url = urlparse(dest)
    if dest_url.scheme == 'file':
        dest_path = pathlib.Path(parse_file_url(dest_url))
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(data)
        if meta is not None:
            xattr.setxattr(dest_path, HELIUM_XATTR, json.dumps(meta).encode('utf-8'))
    elif dest_url.scheme == 's3':
        dest_bucket, dest_path, dest_version_id = parse_s3_url(dest_url)
        if not dest_path or dest_path.endswith('/'):
            raise ValueError("Invalid path: %r" % dest_path)
        if dest_version_id:
            raise ValueError("Cannot set VersionId on destination")
        s3_client.put_object(
            Bucket=dest_bucket,
            Key=dest_path,
            Body=data,
            Metadata={HELIUM_METADATA: json.dumps(meta)}
        )
    else:
        raise NotImplementedError

def get_bytes(src):
    src_url = urlparse(src)
    if src_url.scheme == 'file':
        src_path = pathlib.Path(parse_file_url(src_url))
        data = src_path.read_bytes()
        meta = _parse_file_metadata(src_path)
    elif src_url.scheme == 's3':
        src_bucket, src_path, src_version_id = parse_s3_url(src_url)
        params = dict(Bucket=src_bucket, Key=src_path)
        if src_version_id is not None:
            params.update(dict(VersionId=src_version_id))
        resp = s3_client.get_object(**params)
        data = resp['Body'].read()
        meta = _parse_metadata(resp)
    else:
        raise NotImplementedError
    return data, meta

def get_size_and_meta(src):
    """
    Gets metadata for the object at a given URL.
    """
    src_url = urlparse(src)
    if src_url.scheme == 'file':
        src_path = pathlib.Path(parse_file_url(src_url))
        size = src_path.stat().st_size
        meta = _parse_file_metadata(src_path)
    elif src_url.scheme == 's3':
        bucket, key, version_id = parse_s3_url(src_url)
        params = dict(
            Bucket=bucket,
            Key=key
        )
        if version_id:
            params.update(dict(VersionId=version_id))
        resp = s3_client.head_object(**params)
        size = resp['ContentLength']
        meta = _parse_metadata(resp)
    else:
        raise NotImplementedError
    return size, meta

def calculate_sha256(src_list, total_size):
    lock = Lock()

    with tqdm(total=total_size, unit='B', unit_scale=True) as progress:
        def _process_url(src):
            src_url = urlparse(src)
            hash_obj = hashlib.sha256()
            if src_url.scheme == 'file':
                path = pathlib.Path(parse_file_url(src_url))
                with open(path, 'rb') as fd:
                    while True:
                        chunk = fd.read(1024)
                        if not chunk:
                            break
                        hash_obj.update(chunk)
                        with lock:
                            progress.update(len(chunk))
            elif src_url.scheme == 's3':
                src_bucket, src_path, src_version_id = parse_s3_url(src_url)
                params = dict(Bucket=src_bucket, Key=src_path)
                if src_version_id is not None:
                    params.update(dict(VersionId=src_version_id))
                resp = s3_client.get_object(**params)
                body = resp['Body']
                for chunk in body:
                    hash_obj.update(chunk)
                    with lock:
                        progress.update(len(chunk))
            else:
                raise NotImplementedError
            return hash_obj.hexdigest()

        with ThreadPoolExecutor() as executor:
            results = executor.map(_process_url, src_list)

    return results


def select(url, query, meta=None, alt_s3_client=None, raw=False, **kwargs):
    """Perform an S3 Select SQL query, return results as a Pandas DataFrame

    The data returned by Boto3 for S3 Select is fairly convoluted, to say the
    least.  This function returns the result as a dataframe instead.  It also
    performs the following actions, for convenience:

    * If t4 metadata is given, necessary info to handle the select query is
      pulled from the format metadata.
    * If no metadata is present, but the URL indicates an object with a known
      extension, the file format (and potentially compression) are determeined
      by that extension.
      * Extension may include a compresssion extension in cases where that is
        supported by AWS -- I.e, for queries on JSON or CSV files, .bz2 and
        .gz are supported.
      * Parquet files must not be compressed as a whole, and should not have
        a compression extension.  However, columnar GZIP and Snappy are
        transparently supported.

    Args:
        url(str):  S3 URL of the object to query
        query(str): An SQL query using the 'SELECT' directive. See examples at
            https://docs.aws.amazon.com/AmazonS3/latest/API/RESTObjectSELECTContent.html
        meta: T4 Object Metadata
        alt_s3_client(boto3.client('s3')):  Default client used if not given
        raw(bool):  True to return the raw Boto3 response object
        **kwargs:  s3_client.select() kwargs override.
            All kwargs specified passed to S3 client directly, overriding
            matching default/generated kwargs for `select_object_content()`.
            Note that this will also override the bucket and key specified in
            the URL if `Bucket` and `Key` are passed as kwargs.

    Returns: pandas.DataFrame | dict
        dict is returned if 'raw' is True or if OutputSerialization is set to
            something other than JSON Lines.

    """
    # use passed in client, otherwise module-level client
    s3 = alt_s3_client if alt_s3_client else s3_client
    # We don't process any other kind of response at this time.
    output_serialization = {'JSON': {}}
    query_type = "SQL"  # AWS S3 doesn't currently support anything else.
    meta = meta if meta is not None else {}

    # Internal Format Name <--> S3 Format Name
    valid_s3_select_formats = {
        'parquet': 'Parquet',
        'json': 'JSON',
        'jsonl': 'JSON',
        'csv': 'CSV',
        }
    # S3 Format Name <--> S3-Acceptable compression types
    format_compression = {
        'Parquet': ['NONE'],  # even if column-level compression has been used.
        'JSON': ['NONE', 'BZIP2', 'GZIP'],
        'CSV': ['NONE', 'BZIP2', 'GZIP'],
        }
    # File extension <--> S3-Acceptable compression type
    # For compression type, when not specified in metadata.  Guess by extension.
    accepted_compression = {
        '.bz2': 'BZIP2',
        '.gz': 'GZIP'
        }
    # Extension <--> Internal Format Name
    # For file type, when not specified in metadata. Guess by extension.
    ext_formats = {
        '.parquet': 'parquet',
        '.json': 'json',
        '.jsonl': 'jsonl',
        '.csv': 'csv',
        '.tsv': 'csv',
        '.ssv': 'csv',
        }
    delims = {'.tsv': '\t', '.ssv': ';'}

    parsed_url = urlparse(url)
    bucket, path, version_id = parse_s3_url(parsed_url)

    # TODO: Use formats lib for this stuff
    # use metadata to get format and compression
    compression = None
    format = meta.get('target')
    if format is None:
        format = meta.get('format', {}).get('name')
        if format in ('bzip2', 'gzip'):
            compression = format.upper()
            format = meta.get('format', {}).get('contained_format', {}).get('name')

    # use file extensions to get compression info, if none is present
    exts = pathlib.Path(path).suffixes  # last of e.g. ['.periods', '.in', '.name', '.json', '.gz']
    if exts and not compression:
        if exts[-1].lower() in accepted_compression:
            compression = accepted_compression[exts.pop(-1)]   # remove e.g. '.gz'
    compression = compression if compression else 'NONE'

    # use remaining file extensions to get format info, if none is present
    csv_delim = None
    if exts and not format:
        ext = exts[-1].lower()    # last of e.g. ['.periods', '.in', '.name', '.json']
        if ext in ext_formats:
            format = ext_formats[ext]
            csv_delim = delims.get(ext)
            s3_format = valid_s3_select_formats[format]
            ok_compression = format_compression[s3_format]
            if compression not in ok_compression:
                raise QuiltException("Compression {!r} not valid for select on format {!r}: "
                                     "Expected {!r}".format(compression, s3_format, ok_compression))
    if not format:
        raise QuiltException("Unable to discover format for select on {!r}".format(url))

    # At this point, we have a known format and enough information to use it.
    s3_format = valid_s3_select_formats[format]

    # Create InputSerialization section if not user-specified.
    input_serialization = None
    if 'InputSerialization' not in kwargs:
        input_serialization = {'CompressionType': compression}
        format_spec = input_serialization.setdefault(s3_format, {})

        if s3_format == 'JSON':
            format_spec['Type'] = "LINES" if format == 'jsonl' else "DOCUMENT"
        elif s3_format == 'CSV':
            if csv_delim is not None:
                format_spec['FieldDelimiter'] = csv_delim

    # These are processed and/or default args.
    select_kwargs = dict(
        Bucket=bucket,
        Key=path,
        Expression=query,
        ExpressionType=query_type,
        InputSerialization=input_serialization,
        OutputSerialization=output_serialization,
    )
    # Include user-specified passthrough options, overriding other options
    select_kwargs.update(kwargs)

    response = s3.select_object_content(**select_kwargs)

    # we don't want multiple copies of large chunks of data hanging around.
    # ..iteration ftw.  It's what we get from amazon, anyways..
    def iter_chunks(resp):
        for item in resp['Payload']:
            chunk = item.get('Records', {}).get('Payload')
            if chunk is None:
                continue
            yield chunk

    def iter_lines(resp, delimiter):
        # S3 may break chunks off at any point, so we need to find line endings and handle
        # line breaks manually.
        # Note: this isn't reliable for CSV, because CSV may have a quoted line ending,
        # whereas line endings in JSONLines content will be encoded cleanly.
        lastline = ''
        for chunk in iterdecode(iter_chunks(resp), 'utf-8'):
            lines = chunk.split(delimiter)
            lines[0] = lastline + lines[0]
            lastline = lines.pop(-1)
            for line in lines:
                yield line + delimiter
        yield lastline

    if not raw:
        # JSON used for processed content as it doesn't have the ambiguity of CSV.
        if 'JSON' in select_kwargs["OutputSerialization"]:
            delimiter = select_kwargs['OutputSerialization']['JSON'].get('RecordDelimiter', '\n')
            reader = jsonlines.Reader(line.strip() for line in iter_lines(response, delimiter)
                                      if line.strip())
            # noinspection PyPackageRequirements
            from pandas import DataFrame   # Lazy import for slow module
            # !! if this response type is modified, update related docstrings on Bucket.select().
            return DataFrame.from_records(x for x in reader)
        # If there's some need, we could implement some other OutputSerialization format here.
        # If they've specified an OutputSerialization key we don't handle, just give them the
        # raw response.
    # !! if this response type is modified, update related docstrings on Bucket.select().
    return response
