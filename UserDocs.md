This file documents the T4 Python API, `helium`. `helium` allows you to interact with your T4 instance in Python.

## Installation

Make sure that you have Python 3.6 or higher, and have the [AWS CLI](https://aws.amazon.com/cli/) command line tool (via `pip install aws-cli`).

If this is your first time using AWS, run the following to store the IAM credentials you wish to use with T4:
```
$ aws configure
```

If you already have AWS credentials set up, you may want to initialize your credentials in a Quilt-specific [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html).

Once this is done, install T4 with `pip`:

```
$ pip install git+https://github.com/quiltdata/t4.git#subdirectory=ocean
```

## API reference

Note the format for an S3 path is `BUCKET_NAME/path/to/file/or/dir/`.

### Reading and writing data

![](./notebooks/helium-api.png)

#### `helium.get(src, snapshot=None, version=None)`
Retrieves `src` object from T4 and loads it into memory. Returns a `(data, metadata)` tuple.

Does not work on all objects. For a list of supported objects, see [Serialization](#serialization).

Pass a snapshot hash to the optional `snapshot` parameter to retrieve the state of an S3 object at a given snapshot. Pass a version hash to the optional `version` parameter to retrieve the state of an S3 object at a given version. Only one or none of these two parameters may be specified at a time.

#### `helium.put(obj, dest, meta=dict())`
Writes in-memory object `src` to the `dest` object in T4. Does not work on all objects. For a list of supported objects, see [Serialization](#serialization).

You may specify metadata for the object by pass a dictionary of key-value pairs to the `meta` parameter. For more on metadata, see [Metadata and search](#metadata-and-search).

#### `helium.get_file(src, dest, snapshot=None, version=None)`
Retrieves `src` object from T4, and writes to to the `dest` file on your local disk.

The `snapshot` and `version` optional parameters operate the same as in `helium.get`.

#### `helium.put_file(src, dest, meta=dict())`
Writes local file `src` to the `dest` object in T4.

As with `helium.put`, you may specify metadata for the object by pass a dictionary of key-value pairs to the `meta` parameter. For more on metadata, see [Metadata and search](#metadata-and-search).

#### `helium.delete(path)`
Deletes the object at `path`.

### Snapshots and history

#### `helium.snapshot(path, message)`
Creates a snapshot of the T4 object at `path` with commit message `message`.

#### `helium.list_snapshots(path)`
Lists all snapshots of the T4 object at path. Output consists of path, hash, timestamp, and message.

#### `helium.diff(S3_BUCKET, srchash, desthash)`
Lists differences between two T4 objects: one object with snapshot `srchash` , and one object with snapshot `desthash`.

`S3_BUCKET` may not contain a terminating `/` (temporary limitation)

If the `srchash` and `desthash` are snapshots of the same object, this is effectively a piece of a particular object's history.

If the `srchash` and `desthash` are snapshots of different objects which overlap, this is effectively the difference between two snapshots.

If the `srchash` and `desthash` are snapshots of different objects which do not overlap, this command doesn't make any sense, and you will get an error.

Either of `srchash` or `desthash` may have the value `"latest"`. In this case, the `srchash` or `desthash` wil be compared against the *current* T4 object. This will include changes which have not yet been snapshotted.

#### `helium.diff(srchash, 'latest')`
Lists changes to a T4 object between the snapshot at `srchash` and the object's current state. This includes changes which have not yet been snapshotted.

### Configuration

#### `helium.config()`
Returns an `ordereddict` with the current T4 client configuration details. Configuration is saved to disk.

#### `helium.config(KEY=VALUE [KEY2=VALUE2...])`
Manually sets a specific configuration option.

#### `helium.config(URL)`
Set a configuration option from the URL of a T4 instance.

### Navigation

#### `helium.search(key)`
Searches a T4 instance for `key`. Returns a list of search results. Note that in order for the `search` command to work, you must first connect to your bucket using `helium.config`.

Note that `search` currently automatically adds the `BUCKET_NAME` to any paths you pass to it.

#### `helium.ls(path)`
Enumerates the contents of a path in a T4 instance. This function returns a tuple whose first value is a list of sub-paths, and whose second value is a list of metadata statements about the file. Each version of an object in S3 gets its own entry in the list.

## User guide

### Working with memory

You can commit a Python object to T4 using the `put` command:

```python
# Generate example data
import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.random((1000, 10)))

# Put it
import helium as he
he.put(df, "bucket-name/my-frame.parquet")
```

This will put the `pandas` `DataFrame` created in this example to the top level of the T4 bucket. Note the use of the `parquet` file extension; this is merely for convenience when browsing the bucket, and you may omit a file extension if you so desire.

To put to a sub-folder within the bucket, just include the requisite file path:

```python
he.put(df, "bucket-name/foo/bar/my-frame.parquet")
```

If you put to a folder that doesnt exist yet, `helium` will create that folder for you. If you put another object to the same path, that object will overwrite it; the old object is retained as an older version of the same object.

T4 handles serializing in-memory objects for you. For example, this `DataFrame` will be stored as a `parquet` file, [which serializes and deserializes faster than alternative formats](https://medium.com/@robnewman/e8dbdfb21394). To learn more about T4 serialization, as well as which Python objects are currently supported by T4, skip forward to the section on [Serialization](#serialization).

To read that file back out of T4, use the `get` command:

```python
df, meta = he.get("bucket-name/my-frame.parquet")
```

Notice that `get` returns a tuple of values. The first entry is the data that you put in. The second entry is the metadata associated with the object. If no metadata exists, this value will be `None`.

To learn more about metadata, skip forward to the section on [Metadata and querying](#metadata-and-querying).

### Working with files

The commands for moving files and from T4 are very similar to the ones for moving objects in memory.

To put a file to a T4 object, use the `put_file` command:

```python
# Generate example data
import pandas as pd
import numpy as np
df = pd.DataFrame(np.random.random((1000, 10)))
df.to_csv("my-frame.csv")

# Put it
he.put_file("my-frame.csv", "bucket-name/my-frame.csv")
```

This will populate a CSV file in T4. T4 supports files in any format, and up to 5 TB in size.

Similarly, to get a T4 object back, use the `get_file` command:

```python
df, meta = he.get_file("bucket-name/my-frame.csv", "my-frame.csv")
```

This will download a `my-frame.csv` to your local disk.

Just like `he.get` , this will result in a tuple whose first element is the data and the second, the metadata. If no metadata is present, `None` will be returned.


### Deleting files

To delete a file that's already been committed to T4, use the `delete` command:

```python
he.delete("bucket-name/my-frame.csv")
```

### Versions and snapshots

Object **versions** are automatic and apply to a single object
(provided that your bucket has object versioning enabled).

**Snapshots** are user-created and may apply to zero or more objects. As a
general rule, snapshots apply to entire folders or *paths* in S3.

A snapshot captures the state of an S3 bucket at a particular point in time.
A snapshot contains a *prefix* under which all of the child object versions
are recorded in your bucket's `.quilt/` directory.

Versions and snapshots are *immutable*. Their contents can never change
(until and unless the underlying data or metadata are deleted). Snapshots and
versions are the building blocks of reproducible data pipelines. 

To create a snapshot use the `snapshot` command:

```python
he.snapshot("bucket-name", comment="Initial snapshot.")
```

You may snapshot individual files, folders containing files, or even entire buckets (as in the example above). To list snapshots of an S3 key, use the `list_snapshots` command:

```python
he.list_snapshots("bucket-name")
```

The `get` and `get_file` commands default to returning the current state of an S3 key. To return an S3 key as of a particular snapshot, pass the snapshot hash to the `snapshot` parameter:

```python
he.get("bucket-name/my-frame.csv", snapshot="some_hash_here")
```

#### Short hashes

A snapshot hash is a SHA-256 digest with 64 characters.
You may indentify snapshots with *short hashes*.
Short hashes contain the first few characters of the digest.
In practice, six characters are sufficient to identify a unique
snapshot.

If your bucket has object versioning enabled, you will generally use snapshots for
multiple files.

You can access a specific version of an S3 object using the `version` keyword parameter in `get` or `get_file`:

```python
he.get("bucket-name/my-frame.csv", version="some_hash_here")
```

Use `helium.ls()`, or the web catalog, to display object versions.

### Serialization

#### Built-ins

When you `put` a Python object in T4, the object is transparently serialized
before it gets written. T4 automatically de/serializes the following objects:


| Python Type | Serialization format |
| ------- | ------ |
| `b"string"` | bytes on disk |
| `"string"` | UTF-8 encoded string |
| `pandas.DataFrame` | Parquet |
| `numpy.ndarray` | .np |
| `dict` | JSON | 

> A common choice for serialization is Python's `pickle` module.
Unfortunately, `pickle` is both [slow and insecure](https://www.benfrederickson.com/dont-pickle-your-data/).

####  Custom serializers

To use a serialization format not in the built-ins, like `pickle`, you can do
one of the following:
* `he.put(my_serializer.dumps(obj), "path/to/my/file.ext")`
* Write it to disk, then move it to S3 with `put_file`

### Metadata and search

When you `put` or `put_file` you may optionally pass a dictionary to a `meta` keyword parameter. This metadata is stored alongside your data in the resulting S3 Object.

T4 supports full-text search on a subset of the objects in your S3 bucket (using AWS's [Elasticsearch Service](https://aws.amazon.com/elasticsearch-service/)). Currently Markdown files ending in `md` and Jupyter notebooks ending in `ipynb` are searchable. 

You may search objects in one of two ways. The first way is to go to the T4 Navigator homepage online and use the search bar there. The second way is to use the [`helium.search`](#`helium.search()`) command.

<!-- 

Searching for plaintext is simplest -- just type the terms you want to find into your query, and search will do its best to find matches for those terms. For example, he.search('json') will return all documents that mention json, whether in the key, body of text, or metadata.

Filtering based on metadata is a powerful way to narrow your query. You can currently filter based on exact matches for specific fields in your documents. The syntax is $FIELD:"$VALUE". For example, if you want all the versions of the key example/foo.json, you could he.search('key:"example/foo.json"'). To use nested fields, just put dots between the names of the nested fields. For example, to query documents that have a user-defined metadata property called foo, and a value of 2, use the following query: he.search('user_meta.foo:2') The metadata you can query on are listed below.

The metadata are laid out as follows:

key: string
user_meta: object
type: Create | Delete
version_id: string (S3 version ID)
target: string (file extension of object)
comment: string
updated: date
size: number (file size in bytes)
There are other undocumented properties on documents. Please don't depend on their contents, they may change at any time.

-->

To modify which file types are searchable, populate a `.quilt/config.json` file in your S3 bucket. Note that this file does not exist by default. The contents of the file shoud be something like this:

```json
{
  "ipynb": true,
  "md": true
}
```

## Known issues

* To annotate objects with searchable metadata, you must use the `put` API.
* Plaintext indexing and search does not require the `put` API, but the index
will only contain *newly written objects* with the appropriate file extensions
(*newly written* = created after T4's lambda functions have been attached to your bucket)

* At present, due to limitations with ElasticSearch,
we do not recommend plaintext indexing for files that are over 10 MB in size

* In order to use the entire T4 API, you need sufficient permissions for the underlying S3 bucket. Something like the following:

    ```
    s3:ListBucket
    s3:PutObject
    s3:GetObject
    s3:GetObjectVersion
    ```