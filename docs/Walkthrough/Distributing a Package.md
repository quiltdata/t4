Once your package is ready it's time to save and distribute it.

## Building a package locally

To save a package to your local disk use `build`.

```python
import t4
p = t4.Package()

top_hash = p.build("username/packagename")
```

Building a package requires providing it with a name. Packages names must follow the `${namespace}/${packagename}` format. For small teams, we recommend using the package author's name as the namespace.

## Pushing a package to a remote registry

To share a package with others via a remote registry, `push` it:

```python
import t4
p = t4.Package()
p.push(
    "username/packagename",
    "s3://your-bucket",
    message="Updated version my package"
)
```

`push` targets a *registry*&mdash;a storage backend, currently either an S3 bucket (e.g. `s3://my-bucket`) or a local directory path (e.g. `/path/to/somewhere/`). The registry is infered from the second argument, `dest`. If you omit this argument, the default remot registry will be used:

```python
import t4
t4.config(default_remote_registry='s3://your-bucket')
# this now 'just works'
t4.Package().push("username/packagename")  
```

The default remote registry, if set, persists between sessions.

## Distributing a package version

Once you build `build` or `push` a package, it has a *top_hash*:

```python
import t4

p = t4.Package()
p.build("username/packagename")
p.top_hash

'2a5a67156ca9238c14d12042db51c5b52260fdd5511b61ea89b58929d6e1769b'
```

A top hash is a persistent, immutable reference to a specific version of a package. To ensure that you always download this specific version of this package in the future, provide its top hash.

## Delete a package from a registry

To delete a package from a registry:

```python
import t4

# delete a package in the local registry
t4.delete_package("username/packagename")

# delete a package in a remote registry
t4.delete_package("username/packagename", "s3://your-bucket")
```

Only do this if you really need to as this will break the package for anyone relying on it.