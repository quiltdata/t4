You can install a package either in whole or in part.

## Finding
As explained in ["Building a Package"](Building%20a%20Package.md), packages are managed using **registries**. There is a one local registry on your machine, and potentially many remote registries elsewhere "in the world". Use `list_packages` to see the packages available on a registry:

```
$ python
>>> import t4

>>> t4.list_packages()  # list local packages

["namespace/packagename", "othernamespace/otherpackagename"]

>>> t4.list_packages("s3://my-bucket")  # list remote packages

["user1/seattle-weather", "user2/new-york-ballgames", ...]
```


## Installing

To make a remote package and all of its data available locally, `install` it.

```python
import t4
p = t4.Package.install(
    "username/packagename", 
    "s3://name-of-your-bucket",
    dest="path/to/a/file/location"
)
```

Installing a package downloads all of the data in the package to `dest`. It also imports the package into your local registry.

<!-- TODO: reintroduce this once default file dl config is done
T4 can be configured with a default remote registry (and, in the future, a default file download location), allowing you to omit registry:

```python
# set a default remote registry
t4.config(default_remote_registry="s3://your-bucket")

# install from there implicitly
t4.Package.install("username/packagename")
```
-->

## Browsing
To download a package manifest without downloading its data, use `browse`:

```python
import t4

# load a package from the local registry
p  = t4.Package.browse("username/packagename")

# load a package from a remote registry
p = t4.Package.browse("username/packagename", registry="s3://name-of-your-bucket")
```

`browse` is advantageous when you don't want to download everything in a package at once. Maybe you just want just part of the package, or maybe you just want to look at the metadata.

## Versions
To load a specific version of a package ask for the corresponding **tophash**:

```python
import t4
t4.Package.install(
    "username/packagename", 
    "s3://name-of-your-bucket",
    dest="./",
    pkg_hash="abcd1234"
)
```