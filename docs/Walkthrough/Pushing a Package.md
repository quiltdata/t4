To save a package on your local machine, [you `build` it](./Building A Package). To make it available anywhere else, you `push` it.

For instance:

```python
import t4
p = t4.Package()
tophash = p.push("username/packagename", "<registry>")
```

`push` targets a registry. A **registry** is a storage system&mdash;currently either an S3 bucket or a file system&mdash;which has been configured to support T4 packages.

What is the difference between `push` and `build`? `build` makes your package available in your local registry, e.g. on your machine. `push` makes your package available remotely, e.g. to anyone who has access to a given S3 bucket.

In `git` terms, `build` mirrors `commit`, and `push` mirrors
`push`.

You must specify the registry you are pushing to explicitly. The registry may be either a local filesystem (e.g. `/path/to/somewhere/`) or an S3 bucket configured to work with T4 (e.g. `s3://my-bucket`).
