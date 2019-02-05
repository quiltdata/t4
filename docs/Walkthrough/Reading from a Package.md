Once you have a package definition you can work with it using the package API.

The examples in this section use the following mock package:

```python
import t4
p = (t4.Package()
        .set("trades.parquet", "trades.parquet")
        .set("commodities/gold.csv", "gold.csv")
        .set("commodities/silver.csv", "silver.csv")
    )
```


## Slicing
Use `dict` key selection to slice into a package tree:

```
$ python
>>> p["trades.parquet"]
<<< PackageEntry("trades.parquet")

>>> p["commodities"]
<<< gold.csv
    silver.csv
```

Slicing into a `Package` directory returns another `Package` rooted at that subdirectory. Slicing into a package entry returns an individual `PackageEntry`.


## Downloading data
To download a subset of files from a package directory to a `dest`, use `fetch`:

```python
# download a subfolder
p["commodities"].fetch("./")

# download a single file
p["commodities"]["gold.csv"].fetch("gold.csv")

# download everything
p.fetch("trade-info/")
```

Alternatively, to download data directly into memory:

```
$ python
>>> p["commodities"]["gold.csv"]()

<pandas.DataFrame object at ...>
```

## Reading metadata
Use `get_meta` to load metadata:

```python
# get entry metadata
p["commodities"]["gold.csv"].get_meta()

# get folder metadata
p["commodities"].get_meta()

# get package metadata
p.get_meta()
```