import dedent from 'dedent';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';
import { getBreadCrumbs, isDir, up } from 'utils/s3paths';
import tagged from 'utils/tagged';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import CodeButton from './CodeButton';
import Listing, { ListingItem } from './Listing';
import { displayError } from './errors';
import * as requests from './requests';


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

// TODO: handle revision / hash
const pkgCode = ({ bucket, name }) => dedent`
  import t4
  p = t4.Package.browse("${name}", registry="s3://${bucket}")
`;

export default RT.composeComponent('Bucket.PackageTree',
  AWS.S3.inject(),
  AWS.Signer.inject(),
  withData({
    params: ({ s3, match: { params: { bucket, name, revision } } }) =>
      ({ s3, bucket, name, revision }),
    fetch: requests.fetchPackageTree,
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
    crumbs: [
      Crumb.Segment({
        label: name,
        to: urls.bucketPackageDetail(bucket, name),
      }),
      Crumb.Sep('@'),
      Crumb.Segment({
        label: revision,
        to: urls.bucketPackageTree(bucket, name, revision),
      }),
      Crumb.Sep(': '),
      ...R.intersperse(Crumb.Sep(' / '),
        getBreadCrumbs(path).map(({ label, path: segPath }) =>
          Crumb.Segment({
            label,
            to:
              path === segPath
                ? undefined
                : urls.bucketPackageTree(bucket, name, revision, segPath),
          }))),
    ],
  })),
  withStyles(({ spacing: { unit } }) => ({
    topBar: {
      alignItems: 'center',
      display: 'flex',
      flexWrap: 'wrap',
      marginBottom: 2 * unit,
      marginTop: unit,
    },
    spacer: {
      flexGrow: 1,
    },
    button: {
      color: 'inherit !important',
      marginLeft: unit,
      textDecoration: 'none !important',
    },
  })),
  ({
    classes,
    signer,
    crumbs,
    data: { result, ...data },
    match: { params: { bucket, name } },
  }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        <BreadCrumbs items={crumbs} />
        <div className={classes.spacer} />
        <CodeButton>{pkgCode({ bucket, name })}</CodeButton>
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
        Err: displayError(),
        _: () => <CircularProgress />,
      }, result)}
    </React.Fragment>
  ));
