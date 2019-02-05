Once your package is ready it's time to save and distribute it.

## Building
To save a local package to disk use `build`.

```python
import t4
p = t4.Package()

tophash = p.build("username/packagename")
```

Building a package requires providing it with a name. Packages names must follow the `<authorname>/<packagename>` format.

To rebuild or update a package, just run `build` again.

Built packages are only available to the local user.


## Pushing
To share a package with others via a remote registry, `push` it:

```python
import t4
p = t4.Package()
tophash = p.push(
    "username/packagename", 
    "s3://your-bucket",
    # you can add an optional commit message
    message="Updated version my package"
)
```

`push` targets a registry. A **registry** is a storage backend&mdash;currently either an S3 bucket (e.g. `s3://my-bucket`) or a local directory path (e.g. `/path/to/somewhere/`).

<!-- TODO: move this to another section once config is done
T4 can be configured with a default remote registry. You may omit the registry argument if you provide one:

```python
# set a default remote target
t4.config(default_remote_registry="s3://your-bucket")

# install from there implicitly
t4.Package().push("username/packagename")
```
-->

## Deletion

To delete a package from a registry:

```python
import t4

# delete from local registry
t4.delete_package("username/packagename")

# delete from remote registry
t4.delete_package("username/packagename", "s3://your-bucket")
```

Only do this if you really need to as this will break the package for anyone relying on it.

## Versioning

A successful package `build` or `push` returns a **tophash**.

```
$ python
>>> t4.Package().build("username/packagename")

'2a5a67156ca9238c14d12042db51c5b52260fdd5511b61ea89b58929d6e1769b'
```

A tophash is a persistent, immutable reference to a specific version of a package.