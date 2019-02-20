import { basename } from 'path';

import dedent from 'dedent';
import * as R from 'ramda';
import * as React from 'react';
import CircularProgress from '@material-ui/core/CircularProgress';
import { withStyles } from '@material-ui/core/styles';

import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/StyledLink';
import { composeComponent } from 'utils/reactTools';
import {
  getBreadCrumbs,
  ensureNoSlash,
  withoutPrefix,
  up,
} from 'utils/s3paths';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import CodeButton from './CodeButton';
import Listing, { ListingItem } from './Listing';
import Message from './Message';
import Summary from './Summary';
import { displayError } from './errors';
import * as requests from './requests';


const HELP_LINK =
  'https://github.com/quiltdata/t4/blob/master/UserDocs.md#working-with-buckets';

const code = ({ bucket, path }) => dedent`
  import t4
  b = Bucket("s3://${bucket}")
  # replace ./ to change destination directory
  b.fetch("${path}", "./")
`;

const getCrumbs = R.compose(R.intersperse(Crumb.Sep(' / ')),
  ({ bucket, path, urls }) =>
    [{ label: bucket, path: '' }, ...getBreadCrumbs(path)]
      .map(({ label, path: segPath }) =>
        Crumb.Segment({
          label,
          to: segPath === path ? undefined : urls.bucketDir(bucket, segPath),
        })));

const formatListing = ({ urls }, r) => {
  const dirs = r.dirs.map((name) =>
    ListingItem.Dir({
      name: ensureNoSlash(withoutPrefix(r.path, name)),
      to: urls.bucketDir(r.bucket, name),
    }));
  const files = r.files.map(({ key, size, modified }) =>
    ListingItem.File({
      name: basename(key),
      to: urls.bucketFile(r.bucket, key),
      size,
      modified,
    }));
  const items = [
    ...(
      r.path !== ''
        ? [ListingItem.Dir({
          name: '..',
          to: urls.bucketDir(r.bucket, up(r.path)),
        })]
        : []
    ),
    ...dirs,
    ...files,
  ];
  // filter-out files with same name as one of dirs
  return R.uniqBy(
    ListingItem.case({ Dir: R.prop('name'), File: R.prop('name') }),
    items,
  );
};

export default composeComponent('Bucket.Dir',
  withStyles(({ spacing: { unit } }) => ({
    topBar: {
      alignItems: 'flex-start',
      display: 'flex',
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
  ({ match: { params: { bucket, path = '' } }, classes }) => (
    <NamedRoutes.Inject>
      {({ urls }) => (
        <React.Fragment>
          <div className={classes.topBar}>
            <BreadCrumbs items={getCrumbs({ bucket, path, urls })} />
            <div className={classes.spacer} />
            <CodeButton>{code({ bucket, path })}</CodeButton>
          </div>

          <AWS.S3.Inject>
            {(s3) => (
              <Data
                fetch={requests.bucketListing}
                params={{ s3, bucket, path }}
              >
                {AsyncResult.case({
                  Err: displayError(),
                  Ok: (res) => {
                    const items = formatListing({ urls }, res);
                    return items.length
                      ? (
                        <React.Fragment>
                          <Listing items={items} />
                          <Summary files={res.files} />
                        </React.Fragment>
                      )
                      : (
                        <Message headline="No files">
                          <Link href={HELP_LINK}>
                            Learn how to upload files
                          </Link>.
                        </Message>
                      );
                  },
                  Pending: AsyncResult.case({
                    Ok: (res) => res
                      ? (
                        <React.Fragment>
                          <Listing items={formatListing({ urls }, res)} locked />
                          <Summary files={res.files} />
                        </React.Fragment>
                      )
                      : <CircularProgress />,
                    _: () => null,
                  }),
                  Init: () => null,
                })}
              </Data>
            )}
          </AWS.S3.Inject>
        </React.Fragment>
      )}
    </NamedRoutes.Inject>
  ));
