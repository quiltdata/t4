# Installation

T4 has two components:
* The T4 Python client package
* The T4 web catalog

If you have an already-provisioned catalog, only the Python package is needed.

## T4 client

Python 3.6 is required.

```bash
$ pip install t4
```

If you wish to use AWS resources, such as S3 buckets, you will need valid AWS credentials. If this is your first time using the AWS CLI, run the following:

```bash
$ pip install aws-cli
$ aws configure
```

If you are already using the AWS CLI, you may use your existing profile, or [create a new profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html).

### Developer

Install the current T4 client from `master`:

```bash
$ pip install git+https://github.com/quiltdata/t4.git#subdirectory=api/python
```

## Catalog (Local)

The Javascript catalog is a single-page, static application.
You can build it as follows:

```
$ cd catalog
$ npm run build
```

The static assets, including webpack chunks, are written to `/static`.

For more advanced deployment scripts, see [`deploy_navigator.sh`](../deployment/deploy_navigator.sh).


## Catalog (on AWS)
For instructions on installing the T4 Catalog in AWS see the first section in the [Technical Reference](./Technical%20Reference).