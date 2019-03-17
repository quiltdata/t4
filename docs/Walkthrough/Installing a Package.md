## Searching for packages

As explained in ["Building a Package"](Building%20a%20Package.md), packages are managed using *registries*. There is a one local registry on your machine, and potentially many remote registries elsewhere "in the world". Use `list_packages` to see the packages available on a registry:

```bash
$ python
>>> import t4

>>> t4.list_packages()  # list local packages

["namespace/packagename", "othernamespace/otherpackagename"]

>>> t4.list_packages("s3://my-bucket")  # list remote packages

["user1/seattle-weather", "user2/new-york-ballgames", ...]
```

## Installing a package

To make a remote package and all of its data available locally, `install` it.

```python
import t4
p = t4.Package.install(
    "username/packagename",
    "s3://your-bucket",
)
```

Installing a package downloads all of the data and populates an entry for the package in your local registry.

You can omit `registry` if you configure a default remote registry (this will persists between sessions):

```python
t4.config(default_remote_registry='s3://your-bucket')

# this now 'just works'
t4.Package.install("username/packagename")
```

Data files that you download are written to a folder in your local registry by default. You can specify an alternative destination using `dest`:

```python
t4.Package.install("username/packagename", dest="./")
```

Finally, you can install a specific version of a package by specifying the corresponding top hash:

```python
t4.Package.install("username/packagename", top_hash="abcd1234")
```

## Browsing a package manifest

An alternative to `install` is `browse`. `browse` downloads a package manifest without also downloading the data in the package.

```python
import t4

# load a package manifest from a remote registry
p  = t4.Package.browse("username/packagename", "s3://your-bucket")

# load a package manifest from the default remote registry
p  = t4.Package.browse("username/packagename")

# load a package manifest from the local registry
p = t4.Package.browse("username/packagename", "local")
```

`browse` is advantageous when you don't want to download everything in a package at once. For example if you just want to look at a package's metadata.

## Importing a package

You can import a local package from within Python:

```python
from t4.data.username import packagename
```

This allows you to manage your data and code dependencies all in one place in your Python scripts or Jupyter notebooks.