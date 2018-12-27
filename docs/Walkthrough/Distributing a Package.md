Once you're ready to distribute a package with it's time to save and distribute it.

## Building
To save a local package to disk use `build`.

```python
import t4
p = t4.Package()

tophash = p.build("username/packagename")
```

Building a package requires providing it with a name. Packages names must follow the `<authorname>/<packagename>` format.

To rebuild or update a package, just run `build` again.

## Tophashes
Successfully built packages return a **tophash**.

```
$ python
>>> t4.Package().build("username/packagename")
<<< '2a5a67156ca9238c14d12042db51c5b52260fdd5511b61ea89b58929d6e1769b'
```

A tophash is to a data package what a git hash is to a code package, or a Docker hash to an environment: a persistent, immutable reference to a specific version of a package.

If you `build` a package multiple times, with different data each time, you will get multiple different tophashes. In the future, to refer to a specific version of a package, refer to the corresponding tophash.

## Pushing
To save a package on your local machine `build` it. To make it available on a remote registry, `push` it:

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

`push` targets a registry. A **registry** is a storage system&mdash;currently either an S3 bucket (e.g. `s3://my-bucket`) or a file system (e.g. `/path/to/somewhere/`)&mdash;which has been configured to support T4 packages.

While `build` saves your package locally, `push` saves it on a remote registry, making the package available to anyone with access to the target S3 bucket.

<!-- TODO: move this to another section once config is done
T4 can be configured with a default remote registry. You may omit the registry argument if you provide one:

```python
# set a default remote target
t4.config(default_remote_registry="s3://your-bucket")

# install from there implicitly
t4.Package().push("username/packagename")
```
-->