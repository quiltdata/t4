Once you've created a package you're happy with it's time to save it.

## Building
To save a local package to disk use `build`.

```python
import t4
# create an (empty) package
p = t4.Package()
# build it
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

If you `build` a package multiple times, with different data each time, you will get multiple different tophashes. In the future, to refer to a _specific version_ of a package, you refer to that tophash.

## Pushing
To save a package on your local machine you `build` it. To make it available anywhere else, you `push` it.

For instance:

```python
import t4
p = t4.Package()
tophash = p.push("username/packagename", "<registry>")
```

`push` targets a registry. A **registry** is a storage system&mdash;currently either an S3 bucket or a file system&mdash;which has been configured to support T4 packages.

What is the difference between `push` and `build`? `build` makes your package available in your local registry, e.g. on your machine. `push` makes your package available remotely, e.g. to anyone who has access to a given S3 bucket.

In `git` terms, `build` mirrors `commit`, and `push` mirrors `push`.

You must specify the registry you are pushing to explicitly. The registry may be either a local filesystem (e.g. `/path/to/somewhere/`) or an S3 bucket configured to work with T4 (e.g. `s3://my-bucket`).
