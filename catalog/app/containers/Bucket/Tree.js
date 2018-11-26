import { basename } from 'path';

import * as R from 'ramda';
import * as React from 'react';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import {
  ensureNoSlash,
  getBreadCrumbs,
  isDir,
  up,
  withoutPrefix,
} from 'utils/s3paths';
import { composeComponent } from 'utils/reactTools';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import Listing, { ListingItem } from './Listing';
import Message from './Message';
import Summary from './Summary';


const fetchListing = ({ s3, urls, bucket, path }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Delimiter: '/',
      Prefix: path,
    })
    .promise()
    .then(R.pipe(
      R.applySpec({
        directories: R.pipe(
          R.prop('CommonPrefixes'),
          R.pluck('Prefix'),
          R.filter((d) => d !== '/' && d !== '../'),
          R.uniq,
          R.map((name) =>
            ListingItem.Dir({
              name: ensureNoSlash(withoutPrefix(path, name)),
              to: urls.bucketTree(bucket, name),
            })),
        ),
        files: R.pipe(
          R.prop('Contents'),
          // filter-out "directory-files" (files that match prefixes)
          R.filter(({ Key }) => Key !== path && !Key.endsWith('/')),
          R.map(({ Key, Size, LastModified }) =>
            ListingItem.File({
              name: basename(Key),
              to: urls.bucketTree(bucket, Key),
              size: Size,
              modified: LastModified,
            })),
        ),
      }),
      ({ files, directories }) => [
        ...(
          path !== ''
            ? [ListingItem.Dir({
              name: '..',
              to: urls.bucketTree(bucket, up(path)),
            })]
            : []
        ),
        ...directories,
        ...files,
      ],
      // filter-out files with same name as one of dirs
      R.uniqBy(ListingItem.case({ Dir: R.prop('name'), File: R.prop('name') })),
    ));

const getCrumbs = R.compose(R.intersperse(Crumb.Sep(' / ')),
  ({ bucket, path, urls }) =>
    [{ label: bucket, path: '' }, ...getBreadCrumbs(path)]
      .map(({ label, path: segPath }) =>
        Crumb.Segment({
          label,
          to: segPath === path ? undefined : urls.bucketTree(bucket, segPath),
        })));

export default composeComponent('Bucket.Tree',
  AWS.S3.inject(),
  AWS.Signer.inject(),
  NamedRoutes.inject(),
  withData({
    params: ({ s3, urls, match: { params: { bucket, path } } }) =>
      ({ s3, urls, bucket, path }),
    fetch: fetchListing,
    name: 'listing',
  }),
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
    match: { params: { bucket, path } },
    classes,
    signer,
    listing,
    urls,
  }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        <BreadCrumbs items={getCrumbs({ bucket, path, urls })} />
        {!isDir(path) && (
          <Button
            variant="outlined"
            href={signer.getSignedS3URL({ bucket, key: path })}
            className={classes.button}
          >
            Download file
          </Button>
        )}
      </div>

      {isDir(path)
        ? (
          <React.Fragment>
            <Listing
              {...listing}
              whenEmpty={() => (
                <Message headline="No files">
                  <a href="TODO">Learn how to upload files</a>.
                </Message>
              )}
            />
            <Summary bucket={bucket} path={path} />
          </React.Fragment>
        )
        : (
          <Card>
            <CardContent>
              <ContentWindow handle={{ bucket, key: path }} />
            </CardContent>
          </Card>
        )
      }
    </React.Fragment>
  ));
