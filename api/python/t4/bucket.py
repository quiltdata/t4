import pathlib
from urllib.parse import urlparse

from .data_transfer import (TargetType, copy_file, copy_object, delete_object,
                            deserialize_obj, get_bytes, get_meta,
                            list_objects, put_bytes, serialize_obj)
from .util import QuiltException, fix_url, parse_s3_url

class Bucket(object):
    """
    Implements Bucket interface for T4.
    """
    def __init__(self, bucket_uri):
        """
        Creates a Bucket object.

        Args:
            bucket_uri(str): URI of bucket to target. Must start with 's3://'

        Returns:
            a new Bucket
        """
        parsed = urlparse(bucket_uri)
        bucket, path, version_id = parse_s3_url(parsed)
        if path or version_id:
            raise QuiltException("Bucket URI shouldn't contain a path or a version ID")

        self._uri = 's3://{}/'.format(bucket)
        self._bucket = bucket

    def deserialize(self, key):
        """
        Deserializes object at key from bucket.

        Args:
            key(str): key in bucket to get

        Returns:
            deserialized object

        Raises:
            KeyError if key does not exist
            if deserialization fails
        """
        data, meta = get_bytes(self._uri + key)
        target = meta.get('target', None)
        if not target:
            raise QuiltException("No deserialization metadata, cannot deserialize object")

        target = TargetType(target)
        return deserialize_obj(data, target)

    def __call__(self, key):
        """
        Shorthand for deserialize(key)
        """
        return self.deserialize(key)

    def put(self, key, obj, meta=None):
        """
        Stores obj at key in bucket, optionally with user-provided metadata.

        Args:
            key(str): key in bucket to put object to
            obj(serializable): serializable object to store at key
            meta(dict): optional user-provided metadata to store
        """
        dest = self._uri + key
        meta = meta or {}
        data, target = serialize_obj(obj)
        all_meta = dict(
            target=target.value,
            user_meta=meta
        )
        put_bytes(data, dest, all_meta)

    def put_file(self, key, path):
        """
        Stores file at path to key in bucket.

        Args:
            key(str): key in bucket to store file at
            path(str): string representing local path to file

        Returns:
            None

        Raises:
            if no file exists at path
            if copy fails
        """
        dest = self._uri + key
        copy_file(path, dest)

    def put_dir(self, key, directory):
        """
        Stores all files under directory under the prefix key.

        Args:
            key(str): prefix to store files under in bucket
            directory(str): path to local directory to grab files from

        Returns:
            None

        Raises:
            if directory isn't a valid local directory
            if writing to bucket fails
        """
        # Ensure key ends in '/'.
        if key[-1] != '/':
            key = key + '/'

        src_path = pathlib.Path(directory)
        if not src_path.is_dir():
            raise QuiltException("Provided directory does not exist")

        source_dir = src_path.resolve().as_uri()
        s3_uri_prefix = self._uri + key
        copy_file(source_dir, s3_uri_prefix)

    def keys(self):
        """
        Lists all keys in the bucket.

        Returns:
            list of strings
        """
        return [x.get('Key') for x in list_objects(self._bucket, '')]

    def delete(self, key):
        """
        Deletes a key from the bucket.

        Args:
            key(str): key to delete

        Returns:
            None

        Raises:
            if delete fails
        """
        delete_object(self._bucket, key)

    def fetch(self, key, path):
        """
        Fetches file (or files) at key to path.

        If key ends in '/', then all files with the prefix key will match and will
            be stored in a directory at path.
        Otherwise, only one file will be fetched and it will be stored at path.

        Args:
            key(str): key in bucket to fetch
            path(str): path in local filesystem to store file or files fetched

        Returns:
            None

        Raises:
            if path doesn't exist
            if download fails
        """
        source_uri = self._uri + key
        dest_uri = fix_url(path)
        copy_file(source_uri, dest_uri)

    def get_meta(self, key):
        """
        Gets the metadata associated with a key in bucket.

        Args:
            key(str): key in bucket to get meta for

        Returns:
            dict of meta

        Raises:
            if download fails
        """
        src_uri = self._uri + key
        return get_meta(src_uri)

    def set_meta(self, key, meta):
        """
        Sets user metadata on key in bucket.

        Args:
            key(str): key in bucket to set meta for
            meta(dict): value to set user metadata to

        Returns:
            None

        Raises:
            if put to bucket fails
        """
        dest = self._uri + key
        existing_meta = self.get_meta(dest)
        existing_meta['user_meta'] = meta
        copy_object(self._bucket, key, self._bucket, key, existing_meta)
