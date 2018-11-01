This file documents the T4 Python API, `helium`. `helium` allows you to interact with your T4 instance in Python.

## Installation

Ensure that you have Python 3.6, and the [AWS CLI](https://aws.amazon.com/cli/) (`pip install aws-cli`).

If this is your first time using AWS, run the following to store the IAM credentials you wish to use with T4:
```
$ aws configure
```

You may wish create a Quilt-specific [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html).

Install T4: 

```
$ pip install git+https://github.com/quiltdata/t4.git#subdirectory=api/python
```

## User guide
### Creating a package

To create a new in-memory package you initialize a new Package object and then perform operations on it until you have the Package you want. For example:

	import t4
	# initialize a package
	p = t4.Package()

	# add entries individually using `set`
	p = p.set("foo.csv", "/path/to/local/disk/foo.csv")
	p = p.set("bar.csv", "s3://bucket/path/to/cloud/bar.csv")

	# add many entries at once using `update`
	p = p.update({"baz.csv": "/path/to/baz", "bam.png": "/path/to/bam"})

	# or grab everything in a directory at once using capture
	p = p.capture("/path/to/folder/with/stuff/")

	# delete entries using `delete`
	p = p.delete("bam.png")


### Managing a local package
A local package is one which has not been published yet. Local packages contain local data, so they’re highly malleable. The data they reference may change at any time.

If you would like to save or read a local package, you can use the following methods to do so.

	# save an empty package to the local registry
	p = t4.Package()
	tophash = p.build("example-package")

	# load the package from a local registry
	p = t4.Package("example-package", hash=tophash)

Packages are versioned by top hashes. Every time you build a package you are returned a top hash. To load a specific version of a package from a registry, as here, you can pass the top hash of the desired package version to the `hash` parameter. If you do not specify a top hash, the latest version will be retrieved.


### Publishing a package to T4
Once you have a package manifest you are happy with, you are ready to publish. To publish the package to T4, run the following command:

    p.push("example-package", "s3://name-of-your-t4-bucket/my/package/path")


This will:
* Copy the manifest to T4. The manifest will be stored in your T4 bucket’s package registry by both its top hash and the name you provide (`"example-package"`).
* Copy the package contents to `/my/package/path` in your bucket according to their logical keys.

Once the dataset has been materialized on T4, it will be available to anyone else with access to that T4 bucket.


### Pulling a package from T4
To pull a package that has been published to T4:

	# load the package from the registry
	p = t4.Package("nice-name", registry="name-of-your-t4-bucket")

This will find the manifest associated with the given name and registry and downloads it into memory. This will not download the actual bytes. To do that, you can use `get` or `get_file`:

	# download everything from a package
	p.copy("/", "target/directory/")

	# download a specific entry from a package
	p.copy("foo.parquet", "target/directory/foo.parquet")

	# load a specific entry into memory
    data, meta = p.get("foo.parquet")

Especially with large data packages, there are many cases in which you might want to download a manifest describing a package, without downloading the actual contents of the package itself. For example, you might be interested in a large package with labeled images of cats, dogs, and chickens; but only want the cat pictures. 

This T4 API provides this functionality. Copying over just the files you need allows you to have these cat pictures, without the overhead of downloading the dogs and chickens, too.


<!-- Note that in order for `get` to work, the file must have been created by t4.put and it must be in one of the formats supported by the default T4 deserializers. -->


### Moving data not on T4
We encourage a push/pull architecture based on having data packages ultimately live on T4. But you may also use the t4 CLI to handle moving data anywhere on your local file system.

For example, suppose that you have NAS accessible on your machine from `"nas://"`. All of constructing, pushing, and pulling still work.

To create a package referencing that data and save it locally:

    p = t4.Package()
    p = p.set("foo", "nas://foo")
    p.build("example-package")

To load the contents of that package locally:

	p.copy("/", "target/directory")


Packages pushed to T4 guarantee the immutability of constituent nodes, so long as the underlying S3 bucket has versioning enabled. Packages materialized elsewhere do not. The onus of keeping the package manifest consistent with the actual contents of the file (e.g. updating the package manifest every time the file changes) is on the package author. Additionally, even if package files get overwritten, there is no way of accessing the old files.


### Updating a package
Updating a package in a registry is a matter of pushing to it again with modified contents. For example:

	# push an initial empty package to a T4 bucket
	p = t4.Package()
	p.build("example-package")
	p.push("example-package", "s3://my-t4-bucket")
	
    # change something
    p.set("foo", "/bar.txt")
    
    # push the updated package to the bucket
    p.push("example-package", "s3://my-t4-bucket")


### Reading and writing entry metadata
You can see the metadata associated with individual entries in a package using `get_meta`:

	p.get_meta("foo.csv")

This metadata may be optionally provided to a package entry at definition time by e.g. `set`:

	p.set("foo.csv", meta={"goodness": "very good"})

Metadata is versioned alongside the rest of the package. So if you push a package with changes only to the metadata, e.g. with no changes to the files, you will still generate a new package version and a new tophash.


### Viewing packages available on a registry
In order to successfully download a package from a registry, that package must obviously exist on said registry. To see a list of packages available on a registry, using the `list_packages` command:

    import t4
	t4.list_packages()  # to see local packages
	t4.list_packages("s3://bucket")  # to see remote packages

<!-- ![](img/helium-api.png) -->


### Managing individual files

T4 provides a lower-level API for managing both local and remote files using `t4.copy`:

```python
t4.copy("file:///my-frame.csv", "s3://bucket-name/my-frame.csv")  # copy local to local
t4.copy("s3:///my-frame.csv", "s3://bucket-name/my-frame.csv")  # copy remote to remote
t4.copy("s3://my-frame.csv", "file:///bucket-name/my-frame.csv")  # copy remote to local
```

T4 supports files in any format, and up to 5 TB in size.

To delete a remote file, use the `delete` command:

```python
he.delete("s3://bucket-name/my-frame.csv")
```


### Working with memory

You can save a Python object to a T4 file using the `put` command:

```python
import t4
t4.put(df, "bucket-name/my-frame.parquet")
```

The above code writes `df` at the top level of `bucket-name`.

If you `put` to a folder that doesn't exist yet, `t4` will create that folder. If you overwrite an object, and bucket versioning is enabled, the overwritten object is retained as an older version of the same path. 

T4 transparently serializes and de-serializes select Python
objects. In the above example, `df` is automatically stored as an Apache Parquet file.

To read `df` out of S3 and into local memory, use `get`:

```python
df, meta = he.get("bucket-name/my-frame.parquet")
```

`get` returns a tuple of values. The first entry is the data that you put in. The second entry is the metadata associated with the object. If no metadata exists, this value will be `None`.


### Metadata and search

T4 supports full-text search for select objects, and faceted search for metadata.

`Package.set()` and `Package.update()` take an optional `meta={}` keyword.
The metadata in `meta=` are stored with your data and indexed by T4's search function.

T4 supports full-text search on a subset of the objects in your S3 bucket
(T4 uses [Elasticsearch Service](https://aws.amazon.com/elasticsearch-service/)).
By default, .md (markdown) and .ipynb (Jupyter) files are indexed.
As a result you can search through code and markdown in notebook files.

You may search in two ways:
* With the search bar in your T4 web catalog
* With [`t4.search`](#`t4.search()`) command.

To modify which file types are searchable, populate a `.quilt/config.json` file in your S3 bucket. Note that this file does not exist by default. The contents of the file shoud be something like this:

```json
{
  "ipynb": true,
  "md": true
}
```

By default search covers both plaintext and metadata
(metadata are created via the `meta=` keyword in `Package/set` or `Package.update`).

To search user-defined metadata, perform a search of the form `user_meta.METADATA_KEY:"VALUE"`. For example, to get a list of objects whose metadata contains a value of `bar` for the field `foo`, search for `user_meta.foo:"bar"`.

T4 populates some other metadata fields automatically:

* `key` - the S3 path
* `type` - serialization format
* `version_id` - the object version
* `target` - deserialization format
* `size` - the number of bytes
* `updated` - the current version's timestamp

To search automatic metadata, perform a search of the form `METADATA_KEY:"VALUE"`. For example, to get a list of objects 10 bytes in size, search for `size:"10"`.

## API reference

Coming soon! For now please see the docstrings of individual API methods.


<!--
## Leftovers from the old API reference
### Serialization

#### Built-ins

`put()` transparently serializes Python objects, and `get()` transparently de-serializes Python objects according the following table:

| Python Type | Serialization format |
| ------- | ------ |
| `b"string"` | bytes on disk |
| `"string"` | UTF-8 encoded string |
| `pandas.DataFrame` | Parquet |
| `numpy.ndarray` | .np |
| `dict` | JSON | 


#### No `pickle`?

Since Python's `pickle` module is [slow and insecure](https://www.benfrederickson.com/dont-pickle-your-data/),
T4 does not use `pickle` directly.
In the next section, we'll show you how to use `pickle`
and other custom serialization formats.

#### Custom serializers

To use a custom serialization format not in the built-ins,
you can do one of the following:
* `he.put(my_serializer.dumps(obj), "path/to/my/file.ext")`
* Serialize the object to disk, then call `put_file()`
-->

## Known issues

* To annotate objects with searchable metadata, you must use `T4` API methods.
* The tilde (`~`), forward slash (`/`), back slash, and angle bracket (`{`, `}`, `(`, `)`, `[`, `]`) characters will cause search to fail. If your search string includes these characters, be sure to quote your input. E.g. search for `"~aleksey"`, not `~aleksey`.
* A tilde character (`~`) in an S3 path may cause issues with your operating system and `get_file()`. For local files, use absolute paths (like `/Users/alex/Desktop`) instead.
* The T4 full-text search index only contains *newly written objects* with the appropriate file extensions
(*newly written* = created after T4's lambda functions have been attached to your bucket)
* At present, due to limitations with ElasticSearch, we do not recommend plaintext indexing for files that are over 10 MB in size
* In order to use the entire T4 API, you need sufficient permissions for the underlying S3 bucket. Something like the following:

    ```
    s3:ListBucket
    s3:PutObject
    s3:GetObject
    s3:GetObjectVersion
    ```
* The keys of objects in S3 should not end in `/`. Objects whose keys end in `/`
are treated specially by some S3 tools in a way that
is potentially dangerous, so it's best to avoid them.
The T4 API will therefore reject object keys that end in `/`.
Refer to [Amazon's documentation](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/using-folders.html) on folder objects.

  ~~`he.put_file("foo.txt", "bucket/path/")`~~ - this is not supported

  `he.put_file("local_directory/", "bucket/path/")` - this will perform a recursive copy, and is correct


## Catalog

### Summaries

Quilt summaries summarize data in your bucket.
Summaries combine several file types:

* Markdown (`.md`)
* [Vega specs](https://github.com/vega/vega) (`.json`)
* Jupyter notebooks (`.ipynb`)
* Images (`.jpe?g`, `.png`, `.gif`)
* HTML (`.html`)

Upload `quilt_summarize.json` to any directory where you want a summary
to appear.

`quilt_summarize.json` is a JSON list of supported files in your S3 bucket.
All files in the list are signed (for security) and rendered in order
when you visit the containing directory in the Quilt web catalog.

Paths are resolved relative to the containing `quilt_summarize.json` file.

Example:

```
[
  "/vega_specs/chloropleth.json",
  "./image.jpg",
  "../notebooks/JupyterCon.ipynb",
  "description.md"
]
```
