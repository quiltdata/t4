Data in T4 is organized in terms of **data packages**. A data package is a logical group of files, directories, and metadata that are meaningful.

To create a new package in Python, start by creating a new `Package` object:

```python
import t4
# initialize a package
p = t4.Package()
```

## Setting data in a package

Use the `set` and `set_dir` commands to add individual files and whole directories, respectively, to the `Package`:

```python
# add entries individually using `set`
p = p.set("foo.csv", "/path/to/local/disk/foo.csv")
p = p.set("bar.csv", "s3://bucket/path/to/cloud/bar.csv")

# or grab everything in a directory at once using `set_dir`
p = p.set_dir("stuff/", "/path/to/folder/with/stuff/")
```

The first parameter to these functions is the **logical key**— where the file lives *within* the package. The second is the **physical key**—where the file is actually located.

Packages currently support two kinds of entries: local files, and S3 objects. To add an S3 object to a package, as above, use the `s3://<NAME>` prefix, where `<NAME>` is the name of your S3 bucket. Local files do not need a prefix, but may optionally be prefixed with `file:///`.

You can also add multiple files at once using `update`:

```python
# add many entries at once using `update`
p = p.update({
    "baz.csv": "/path/to/baz",
    "bam.png": "/path/to/bam"
})
```

Of course you can also delete entries:

```python
p.delete("bam.png")
```

## Setting metadata in a package

Packages support **metadata**. Metadata can be set on any entry or directory in the package, as well as on the package itself.

You can use the `meta` parameter, available on all of `set`, `set_dir`, and `update`, to set entry metadata at package creation time.

```python
(
    t4.Package()
        .set("foo.csv", "foo.csv", meta={"filetype": "csv"})
        .set_dir("stuff/", "stuff/", meta={"origin": "unknown"})
)
```

You can set metadata for the package as a whole using `set_meta`.

```python
# set metadata on a package
p.set_meta({"package-type": "demo"})
```
