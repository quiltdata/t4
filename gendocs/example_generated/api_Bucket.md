
# Bucket(self, bucket\_uri)
Bucket interface for T4.

**\_\_init\_\_**

Creates a Bucket object.

__Arguments__

* __bucket\_uri(str)__:  URI of bucket to target. Must start with 's3://'

__Returns__

a new Bucket

## Bucket.\_\_call\_\_(self, key)
Deserializes object at key from bucket.

`bucket(key)`, Shorthand for `bucket.deserialize(key)`

__Arguments__

* __key__:  Key of object to deserialize


## Bucket.config(self, config\_url='https://t4.quiltdata.com/config.json', quiet=False)

Updates this bucket's search endpoint based on a federation config.


## Bucket.delete(self, key)

Deletes a key from the bucket.

__Arguments__

* __key(str)__:  key to delete

__Returns__

None

__Raises__

* if delete fails


## Bucket.deserialize(self, key)

Deserializes object at key from bucket.

__Arguments__

* __key(str)__:  key in bucket to get

__Returns__

deserialized object

__Raises__

* `KeyError`:  if key does not exist
* `QuiltException`:  if deserialization fails in a known way
* if a deserializer raises an unexpected error


## Bucket.fetch(self, key, path)

Fetches file (or files) at key to path.

If key ends in '/', then all files with the prefix key will match and
will be stored in a directory at path.

Otherwise, only one file will be fetched and it will be stored at path.

__Arguments__

* __key(str)__:  key in bucket to fetch
* __path(str)__:  path in local filesystem to store file or files fetched

__Returns__

None

__Raises__

* if path doesn't exist
* if download fails


## Bucket.get\_meta(self, key)

Gets the metadata associated with a key in bucket.

__Arguments__

* __key(str)__:  key in bucket to get meta for

__Returns__

dict of meta

__Raises__

* if download fails


## Bucket.keys(self)

Lists all keys in the bucket.

__Returns__

list of strings


## Bucket.put(self, key, obj, meta=None)

Stores obj at key in bucket, optionally with user-provided metadata.

__Arguments__

* __key(str)__:  key in bucket to put object to
* __obj(serializable)__:  serializable object to store at key
* __meta(dict)__:  optional user-provided metadata to store


## Bucket.put\_dir(self, key, directory)

Stores all files under directory under the prefix key.

__Arguments__

* __key(str)__:  prefix to store files under in bucket
* __directory(str)__:  path to local directory to grab files from

__Returns__

None

__Raises__

* if directory isn't a valid local directory
* if writing to bucket fails


## Bucket.put\_file(self, key, path)

Stores file at path to key in bucket.

__Arguments__

* __key(str)__:  key in bucket to store file at
* __path(str)__:  string representing local path to file

__Returns__

None

__Raises__

* if no file exists at path
* if copy fails


## Bucket.search(self, query)

Execute a search against the configured search endpoint.

__Arguments__

* __query (str)__:  query string to search

__Returns__

either the request object (in case of an error) or
a list of objects with the following structure:
```
[{
    "key": <key of the object>,
    "version_id": <version_id of object version>,
    "operation": <"Create" or "Delete">,
    "meta": <metadata attached to object>,
    "size": <size of object in bytes>,
    "text": <indexed text of object>,
    "source": <source document for object (what is actually stored in ElasticSeach)>,
    "time": <timestamp for operation>,
}...]
```


## Bucket.select(self, key, query, raw=False)

Selects data from an S3 object.

__Arguments__

* __key(str)__:  key to query in bucket
* __query(str)__:  query to execute (SQL by default)
* __query\_type(str)__:  other query type accepted by S3 service
* __raw(bool)__:  return the raw (but parsed) response

__Returns__

`pandas.DataFrame`: with results of query


## Bucket.set\_meta(self, key, meta)

Sets user metadata on key in bucket.

__Arguments__

* __key(str)__:  key in bucket to set meta for
* __meta(dict)__:  value to set user metadata to

__Returns__

None

__Raises__

* if put to bucket fails
