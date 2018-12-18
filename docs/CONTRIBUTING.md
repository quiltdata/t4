T4 is an open source project, and we welcome contributions from the community.

Contributors must adhere to the [Code of Conduct](https://github.com/quiltdata/quilt/blob/master/docs/CODE_OF_CONDUCT.md).

## Reporting issues
Unsure about something? To get support, check out our [Slack channel](https://quiltusers.slack.com/messages).

Found a bug? File it in our [GitHub issues](https://github.com/quiltdata/t4/issues).

## Cloning
To work on `t4` you will first need to clone the repository.

```bash
$ git clone https://github.com/quiltdata/t4
```

You can then set up your own branch version of the code, and work on your changes for a pull request from there.

```bash
$ cd t4
$ git checkout -B new-branch-name
```

## Local package development
### Environment
Use `pip` to install `t4` locally (including development dependencies):

```bash
$ cd api/python
$ pip install -e .[extra]
```

This will create an [editable install](https://pip.pypa.io/en/stable/reference/pip_install/#editable-installs) of `t4`, allowing you to modify the code and test your changes right away.

### Testing
All new code contributions are expected to have complete unit test coverage, and to pass all preexisting tests.

Use `pytest` to test your changes during normal development. To run `pytest` on the entire codebase:

```bash
$ cd api/python/tests
$ pytest
```

When your branch is ready, you may run `tox` or `detox` to test a new install. To additionally test dependencies use `detox --refresh`, which will reset the environment it creates.

## Local catalog development
### Environment
Use `npm` to install the catalog (`t4-navigator`) dependencies locally:

```bash
$ cd catalog
$ npm install
```

There is one known issue with installation. At time of writing, the `t4-navigator` package depends on `iltorb@1.3.10`, which may lack prebuilt binaries for your platform and may fall back on building from source using `node-gyp`. `node-gyp` depends on Python 2; if you only have Python 3 in your install environment it will fail.

To fix this, point `npm` to a Python 2 path on your machine. For example on macOS:

```bash
$ npm config set python /usr/bin/python
$ npm install
```

### Build
To build a static code bundle, as would be necessary in order to serve the catalog:

```bash
$ npm run build
```

To run the catalog is developer mode:

```bash
$ npm start
```

This uses `webpack` under the hood to compile code changes on the fly and provide live reloading, useful when developing.

Make sure that any images you check into the repository are [optimized](https://kinsta.com/blog/optimize-images-for-web/) at check-in time.

### Testing
To run the catalog unit tests:

```bash
npm run test
```

## License

Quilt is open source under the [Apache License, Version 2.0](https://github.com/quiltdata/quilt/tree/7a4a6db12839e2b932847db5224b858da52db200/LICENSE/README.md).
