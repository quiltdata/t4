## Finding
Before you can install a package you need to know that it exists, and how to get it.

As explained in ["Building a Package"](Building%20a%20Package.md), packages are managed using **registries**. There is a one local registry on your machine, and potentially many remote registries elsewhere "in the world".

Use `list_packages` to see which packages are available where. `list_packages` works on local and remote registries alike:

```
$ python
>>> import t4

>>> t4.list_packages()  # list local packages
<<< ["username/packagename", "otherusername/otherpackagename"]

>>> t4.list_packages("s3://my-bucket")  # list remote packages
<<< ["user1/seattle-weather", "user2/new-york-ballgames", ...]
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

`install` starts by downloading the **package manifest**&mdash;essentially a `list` of things in the package. It then takes each file referenced by the package and downloads it to your `dest`.

Once you `install` a remote package it becomes a local package, available in your local registry.

## Browsing
To open a local package, use `browse`:

```python
import t4
p  = t4.Package.browse("username/packagename")
```

You can also use `browse` on a remote package:

```python
p = t4.Package.browse("username/packagename", registry="s3://name-of-your-bucket")
```

`browse` opens (if necessary, downloads) a package manifest. It does not move any data. This is advantageous (over `install`) when you don't want to download a large package all at once; you just want to see what's inside it.

To learn how to introspect a package see the next section: [Inspecting A Package](Introspecting%20A%20Package.md).

## Versions
As explained in the section ["Building a Package"](Building%20a%20Package.md), individual packages are versioned using a _tophash_. Different packages with the same name but different data will have different tophashes.

Use the `tophash` parameter to `install` or `browse` a specific version of a package.

```python
import t4

# install a specific package version
p = t4.Package.install(
    "username/packagename", 
    "s3://name-of-your-bucket",
    dest="path/to/a/file/location",
    tophash="abcd1234"
)

# browse a specific package version
p = t4.Package.browse(
    "username/packagename", 
    registry="s3://name-of-your-bucket",
    tophash="abcd1234"
)
```