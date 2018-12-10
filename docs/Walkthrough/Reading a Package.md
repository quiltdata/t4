In the sections ["Creating A Package""](Creating%20a%20Package.md) and ["Installing A Package"](./Installing A Package), we saw how to create a package from scratch and how to download a package from somewhere else, respectively.

Once you have a package it's easy to introspect it. Suppose we have the following example package:

```python
import t4
p = (t4.Package()
        .set("trades.parquet", "trades.parquet")
        .set("commodities/gold.csv", "gold.csv")
        .set("commodities/silver.csv", "silver.csv")
    )
```


## Selection
To dig into a package tree:

```
$ python
>>> p["trades.parquet"]
<<< PackageEntry("trades.parquet")

>>> p["commodities"]
<<< gold.csv
    silver.csv
```

Slicing into a `Package` directory returns another `Package` rooted at that subdirectory. Slicing into a package entry returns an individual `PackageEntry`.


## Downloading to a file
To download a subset of files from a package directory to a `dest`, use `fetch`:

```python
# download a subfolder
p["commodities"].fetch("<dest>")

# download a file
p["commodities"]["gold.csv"].fetch("<dest>")

# download everything
p.fetch("<dest>")
```


## Downloading into memory
Alternatively, you can download data directly into memory using `deserialize`:

```
$ python
>>> p["commodities"]["gold.csv"].deserialize()
<<< <pandas.DataFrame object at ...>

>>> p["commodities"]["gold.csv"]()  # sugar
<<< <pandas.DataFrame object at ...>
```

## Reading metadata
Finally, to read the metadata for a file, folder, or package use `get_meta`:

```python
# get entry metadata
p["commodities"]["gold.csv"].get_meta()

# get folder metadata
p["commodities"].get_meta()

# get package metadata
p.get_meta()
```