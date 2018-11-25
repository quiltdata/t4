import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';
import { isDir, up } from 'utils/s3paths';
import tagged from 'utils/tagged';

import Listing, { ListingItem } from './Listing';
import * as packages from './packages';


const splitPath = R.pipe(R.split('/'), R.reject(R.isEmpty));

const TreeDisplay = tagged([
  'File', // key
  'Dir', // [...files]
]);

const computeTree = ({ urls, bucket, name, revision, path }) => R.pipe(
  R.prop('keys'),
  R.ifElse(
    () => isDir(path),
    R.pipe(
      R.map((info) => {
        // eslint-disable-next-line camelcase
        const segments = info.logical_key.split('/');
        const dir = R.init(segments);
        const file = R.last(segments);
        return { dir, file, ...info };
      }),
      R.applySpec({
        dirs: R.pipe(
          R.pluck('dir'),
          R.uniq,
          R.filter((dir) => dir.length > 0 && R.equals(R.init(dir), splitPath(path))),
          R.map((dir) =>
            ListingItem.Dir({
              name: R.last(dir),
              to: urls.bucketPackageTree(bucket, name, revision, `${dir.join('/')}/`),
            })),
        ),
        files: R.pipe(
          R.filter(({ dir }) => R.equals(dir, splitPath(path))),
          R.map(({ dir, file, size }) =>
            ListingItem.File({
              name: file,
              to: urls.bucketPackageTree(bucket, name, revision,
                [...dir, file].join('/')),
              size,
            })),
        ),
      }),
      ({ dirs, files }) => TreeDisplay.Dir([
        ...(
          path !== ''
            ? [ListingItem.Dir({
              name: '..',
              to: urls.bucketPackageTree(bucket, name, revision, up(path)),
            })]
            : []
        ),
        ...dirs,
        ...files,
      ]),
    ),
    R.pipe(
      R.find(R.propEq('logical_key', path)),
      // TODO: throw NotFound
      ({ physical_keys: [key] }) =>
        TreeDisplay.File(key.replace(`s3://${bucket}/`, '')),
    ),
  ),
);

export default RT.composeComponent('Bucket.PackageTree',
  AWS.S3.inject(),
  AWS.Signer.inject(),
  withData({
    params: ({ s3, match: { params: { bucket, name, revision } } }) =>
      ({ s3, bucket, name, revision }),
    fetch: packages.fetchTree,
  }),
  NamedRoutes.inject(),
  RC.withProps(({
    data,
    urls,
    match: { params: { bucket, name, revision, path } },
  }) => ({
    data: R.evolve({
      result: AsyncResult.case({
        Ok: R.pipe(computeTree({ urls, bucket, name, revision, path }), AsyncResult.Ok),
        Pending: AsyncResult.case({
          Ok: R.pipe(computeTree({ urls, bucket, name, revision, path }), AsyncResult.Ok),
          _: R.identity,
        }),
        _: R.identity,
      }),
    }, data),
  })),
  withStyles(({ spacing: { unit } }) => ({
    topBar: {
      alignItems: 'baseline',
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'space-between',
      marginBottom: 2 * unit,
      marginTop: unit,
    },
    button: {
      color: 'inherit !important',
      textDecoration: 'none !important',
    },
  })),
  ({
    classes,
    urls,
    signer,
    data: { result, ...data },
    match: { params: { bucket, name, revision, path } },
  }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        {/* TODO: non-bold */}
        <Typography variant="h6">
          <Link to={urls.bucketPackageDetail(bucket, name)}>{name}</Link>
          @
          <Link to={urls.bucketPackageTree(bucket, name, revision)}>{revision}</Link>
          :
          {/* TODO: crumbs */}
          {path}
        </Typography>
        {AsyncResult.case({
          Ok: TreeDisplay.case({
            File: (key) => (
              <Button
                variant="outlined"
                href={signer.getSignedS3URL({ bucket, key })}
                className={classes.button}
              >
                Download file
              </Button>
            ),
            _: () => null,
          }),
          _: () => null,
        }, result)}
      </div>
      {AsyncResult.case({
        Ok: TreeDisplay.case({
          File: (key) => (
            <Card>
              <CardContent>
                <ContentWindow handle={{ bucket, key }} />
              </CardContent>
            </Card>
          ),
          Dir: (dir) => <Listing result={AsyncResult.Ok(dir)} {...data} />,
        }),
        Err: (e) => <h1>Error: {e.message}</h1>,
        _: () => <CircularProgress />,
      }, result)}
    </React.Fragment>
  ));
