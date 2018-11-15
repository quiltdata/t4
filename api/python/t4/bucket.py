import pathlib

from .data_transfer import (copy_file, delete_object, list_objects,
                            put_bytes, serialize_obj)
from .util import QuiltException, fix_url

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
        if not bucket_uri.startswith('s3://'):
            raise QuiltException("Bucket URI must start with s3://")
        self._uri = bucket_uri.strip('/') + '/'
        self._bucket = self._uri[5:] # remove 's3://'
        self._bucket = self._bucket.strip('/') # remove trailing '/'

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
        pass

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
        put_bytes(data, fix_url(dest), all_meta)

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

        files = src_path.rglob('*')
        for f in files:
            if not f.is_file():
                continue
            new_key = key + f.relative_to(src_path).as_posix()
            new_path = self._uri + new_key
            copy_file(f.resolve().as_uri(), new_path)

    def keys(self):
        """
        Lists all keys in the bucket.

        Returns:
            list of strings
        """
        return list(map(lambda x: x.get('Key'), list_objects(self._bucket, '')))

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
        if not key.endswith('/'):
            copy_file(self._uri + key, fix_url(path))
            return

        objects = list_objects(self._bucket, key)
        for o in objects:
            okey = o['Key']
            def remove_prefix(text, prefix):
                return text[text.startswith(prefix) and len(prefix):]

            relative_key = remove_prefix(okey, key)
            new_location = path + relative_key
            copy_file(fix_url(self._uri + okey), fix_url(new_location))

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
        pass

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
        pass
