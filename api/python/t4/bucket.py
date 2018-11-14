

class Bucket(object):
    """
    Implements Bucket interface for T4.
    """
    def __init__(bucket_uri):
        self._uri = bucket_uri

    def deserialize(key):
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

    def __call__(key):
        """
        Shorthand for deserialize(key)
        """
        return self.deserialize(key)

    def put(key, obj, meta=None):
        """
        Stores obj at key in bucket, optionally with user-provided metadata.

        Args:
            key(str): key in bucket to put object to
            obj(serializable): serializable object to store at key
            meta(dict): optional user-provided metadata to store
        """
        meta = meta or {}
        pass

    def put_file(key, path):
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
        pass

    def put_dir(key, directory):
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
        pass

    def keys():
        """
        Lists all keys in the bucket.

        Returns:
            list of strings
        """
        pass

    def delete(key):
        """
        Deletes a key from the bucket.

        Args:
            key(str): key to delete

        Returns:
            None

        Raises:
            if delete fails
        """
        pass

    def fetch(key, path):
        """
        Fetches file (or files) at key to path.

        If key ends in '/', then all files with the prefix key will match and will
            be stored in a directory at path.
        Otherwise, only one file will be fetched and it will be stored at path.

        Args:
            key(str): key in bucket to fetch
            path(str): path in local filesystem to store file or files fetched

        Raises:
            if path doesn't exist
            if download fails
        """
        pass

    def get_meta(key):
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

    def set_meta(key, meta):
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
