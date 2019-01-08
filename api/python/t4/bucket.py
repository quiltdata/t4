"""
bucket.py

Contains the Bucket class, which provides several useful functions
    over an s3 bucket.
"""
import json
import pathlib
from urllib.parse import urlparse

from .data_transfer import (TargetType, copy_file, copy_object, delete_object,
                            deserialize_obj, get_bytes, get_size_and_meta,
                            list_objects, put_bytes, select, serialize_obj,
                            list_object_versions)
from .search_util import search
from .util import QuiltException, find_bucket_config, fix_url, parse_s3_url


CONFIG_URL = "https://t4.quiltdata.com/config.json"


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
        self._search_endpoint = None

    def config(self, config_url=CONFIG_URL):
        """
        Updates this bucket's search endpoint based on a federation config.
        """
        bucket_config = find_bucket_config(self._bucket, config_url)
        if 'searchEndpoint' in bucket_config:
            self._search_endpoint = bucket_config['searchEndpoint']
        elif 'search_endpoint' in bucket_config:
            # old format
            self._search_endpoint = bucket_config['search_endpoint']

    def search(self, query):
        """
        Execute a search against the configured search endpoint.

        query: query string to search

        Returns either the request object (in case of an error) or
                a list of objects with the following keys:
            key: key of the object
            version_id: version_id of object version
            operation: Create or Delete
            meta: metadata attached to object
            size: size of object in bytes
            text: indexed text of object
            source: source document for object (what is actually stored in ElasticSeach)
            time: timestamp for operation

        """
        if not self._search_endpoint:
            self.config()
        return search(query, self._search_endpoint)

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
        copy_file(fix_url(path), dest)

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
        if not key:
            raise QuiltException("Must specify the key to delete")

        if key[-1] == '/':
            raise QuiltException("Must use delete_dir to delete directories")

        delete_object(self._bucket, key)

    def delete_dir(self, path):
        """Delete a directory and all of its contents from the bucket.

        Parameters:
                path (str): path to the directory to delete
        """
        results = list_objects(self._bucket, path)
        for result in results:
            self.delete(result['Key'])

    def ls(self, path=None, recursive=False):
        """List data from the specified path.

        Parameters:
            path (str): bucket path to list
            recursive (bool): show subdirectories and their contents as well

        Returns:
            ``list``: Return value structure has not yet been permanently decided
            Currently, it's a ``tuple`` of ``list`` objects, containing the
            following:
            result[0]
                directory info
            result[1]
                file/object info
            result[2]
                delete markers
        """
        if path and not path.endswith('/'):
            path += '/'
        elif not path:
            path = ""  # enumerate top-of-bucket

        results = list_object_versions(self._bucket, path, recursive=recursive)
        return results

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
        return get_size_and_meta(src_uri)[1]

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
        existing_meta = self.get_meta(key)
        existing_meta['user_meta'] = meta
        copy_object(self._bucket, key, self._bucket, key, existing_meta)

    def select(self, key, query, raw=False):
        """
        Selects data from an S3 object.

        Args:
            key(str): key to query in bucket
            query(str): query to execute (SQL by default)
            query_type(str): other query type accepted by S3 service
            raw(bool): return the raw (but parsed) response
        Returns:
            pandas.DataFrame with results of query
        """
        meta = self.get_meta(key)
        uri = self._uri + key
        return select(uri, query, meta=meta, alt_s3_client=None, raw=raw)
