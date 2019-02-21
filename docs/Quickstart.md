This page is a five-minute introduction to the T4 Python API. To try out the T4 catalog, [visit the demo catalog](https://alpha.quiltdata.com/b/quilt-example).

## Data packages

The core concept in T4 is that of a **data package**. A data package is a logically self contained group of files which provide some unit of value.

For example, suppose that you are a data scientist analyzing October sales at an apparel store. Your code might depend on the following set of files:

```bash
october_2018_clothing_sales
    sales-snapshot-11-01.parquet
    sales-snapshot-11-02.parquet
    ...
    sales-snapshot-11-31.parquet
```

T4 allows you to create, edit, and distribute groups of files like this one as a single cohesive group&mdash;a data package. This gives your data a host of useful properties:

* **modularization**&mdash;data packages allow you express your data dependencies the same way you express your code dependencies: in groups of functional, well-documented modules
* **versioning**&mdash;data packages provide version control for data
* **reproducibility**&mdash;data packages are immutable and persistent, ensuring continuous reproducibility
* **accessibility**&mdash;anyone with access to your T4 instance can browse, explore, download, and even reuse your data package

## Before you begin

To get started, you will first need to [install the `t4` Python package](./Installation.md). Then import it:

```python
import t4
```

For demo purposes we will use a small dataset tracking an 1851 hurricane in the Atlantic Ocean, which we'll persist to disk immediately:

```python
import pandas as pd
data = pd.DataFrame({
    'id': ['AL011851']*5,
    'name': ['Unnamed']*5,
    'date': [f'1851-06-25 {hr}:00:00' for hr in 
             ['00', '06', '12', '18', '21']],
    'status_of_system': ['HU']*5,
    'latitude': [28.0, 28.0, 28.0, 28.1, 28.2],
    'longitude': [-94.8, -95.4, -96.0, -96.5, -96.8]
})
data.to_csv("atlantic-storm.csv")
```

## Creating a package

To initialize an in-memory data package, use the `Package` constructor:

```python
# define a package
p = t4.Package()
```

Use `set` to add a file to a package, or `set_dir` to add an entire folder:

```python
# add a file
p.set('storms/atlantic-storm.csv', "atlantic-storm.csv")
# add a folder
p.set_dir('storms/', './')
```

You can point a package key at any local file or S3 key.

Packages support metadata on data nodes (directories too):

```python
p.set('storms/atlantic-storm.csv', 'atlantic-storm.csv', meta={'ocean':'atlantic'})
```

Packages mimic `dict` objects in their behavior. So to introspect a package, key into it using a path fragment:

```bash
p['storms']  # outputs just "atlantic-storms.csv"
```

You can interact with directories and files inside of a package once you're at their key. For example, use `get_meta` to get the metadata:

```python
p['storms/atlantic-storms.csv'].get_meta()
# outputs {'side': 'atlantic'}
```

Use `fetch` to download the data to a file or a directory:

```python
p['storms/atlantic-storms.csv'].fetch('another-copy-of-storms.csv')
```

You can also load certain types of entries directly into memory:

```python
p['storms/atlantic-storms.csv']()
# outputs <pandas.DataFrame at ...>
```

## Pushing a package

Suppose that you've create a package and want to share it with the rest of your team. T4 allows you to do so by pushing your package to a T4 **catalog**, which sits on top of an S3 bucket and allows anyone with access to that bucket to see, push, and download packages in that bucket.

Note that this section, and the next, require a catalog you have access to.

To make a package available on (and downloadable from) a catalog, use `push`, parameterized with the name of the package (a `username/packagename` pair) and the identifier for the S3 bucket you are pushing to:

```python
p.push('username/packagename', 's3://your-bucket')
```

Alternatively, you may wish to save a package locally. To do this, use `build`:

```python
p.build('username/packagename')
```

## Installing a package

To see all the packages available on a catalog, use `list_packages`:

```python
t4.list_packages('s3://your-bucket')
# outputs ['username/packagename', 'foo/bar']
```

To download a package and all of its data from a remote catalog to a `dest` on your machine, `install` it.

```python
p = t4.Package.install('username/packagename', 's3://your-bucket', dest='temp_folder/')
```

You can also choose to download just the  **package manifest** without downloading the data files it references. A package manifest is a simple JSON metadata file that is independent of the actual package data:

```python
# get just the manifest, not the data
p = t4.Package.browse('username/packagename', 's3://your-bucket')
```

`browse` is useful when you only need part of a package, or only want to inspect a package's metadata. You can `browse`, then `fetch`, to get data of interest:

```python
p = t4.Package.browse('username/packagename', 's3://your-bucket')
p['resources'].fetch('temp/')
```

## Importing a package

Once you've installed a package locally you can import it in Python.

```python
from t4.data.username import packagename
```

This lets you manage the data and code dependencies in your code all in one place!