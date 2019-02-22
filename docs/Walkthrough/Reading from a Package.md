Once you have a package definition you can work with it using the package API.

The examples in this section use the following mock package:

```python
import t4
p = (t4.Package()
        .set("trades.parquet", "trades.parquet")
        .set("symbols.yaml", "symbols.yaml")
        .set("commodities/gold.csv", "gold.csv")
        .set("commodities/silver.csv", "silver.csv")
    )
```

## Slicing through a package

Use `dict` key selection to slice into a package tree:

```bash
$ python
>>> p["trades.parquet"]
<<< PackageEntry("trades.parquet")

>>> p["commodities"]
<<< gold.csv
    silver.csv
```

Slicing into a `Package` directory returns another `Package` rooted at that subdirectory. Slicing into a package entry returns an individual `PackageEntry`.

## Downloading package data to disk

To download a subset of files from a package directory to a `dest`, use `fetch`:

```python
# download a subfolder
p["commodities"].fetch("./")

# download a single file
p["commodities"]["gold.csv"].fetch("gold.csv")

# download everything
p.fetch("trade-info/")
```

## Downloading package data into memory

Alternatively, you can download data directly into memory:

```bash
$ python
>>> p["commodities"]["gold.csv"]()
<<< <pandas.DataFrame object at ...>
```

To apply a custom deserializer to your data, pass the function as a parameter to the function. For example, to load a `yaml` file using `yaml.safe_load`:

```bash
$ python
>>> p["symbols.yaml"](yaml.safe_load)
<<< {'gold': 'au', 'silver': 'ag'}
```

The deserializer should accept a byte stream.

## Reading package metadata

Use `get_meta` to load metadata:

```python
# get entry metadata
p["commodities"]["gold.csv"].get_meta()

# get folder metadata
p["commodities"].get_meta()

# get package metadata
p.get_meta()
```