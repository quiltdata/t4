import { basename } from 'path';

import dedent from 'dedent';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/StyledLink';
import { composeComponent } from 'utils/reactTools';
import {
  getBreadCrumbs,
  isDir,
} from 'utils/s3paths';
import withParsedQuery from 'utils/withParsedQuery';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import CodeButton from './CodeButton';
import Listing from './Listing';
import Message from './Message';
import Summary from './Summary';
import { displayError } from './errors';
import * as requests from './requests';


const getCrumbs = R.compose(R.intersperse(Crumb.Sep(' / ')),
  ({ bucket, path, urls }) =>
    [{ label: bucket, path: '' }, ...getBreadCrumbs(path)]
      .map(({ label, path: segPath }) =>
        Crumb.Segment({
          label,
          to: segPath === path ? undefined : urls.bucketTree(bucket, segPath),
        })));

const dirCode = ({ bucket, path }) => dedent`
  import t4
  b = Bucket("s3://${bucket}")
  # replace ./ to change destination directory
  b.fetch("${path}", "./")
`;

const fileCode = ({ bucket, path }) => dedent`
  import t4
  b = Bucket("s3://${bucket}")
  # replace ./${basename(path)} to change destination file
  b.fetch("${path}", "./${basename(path)}")
`;

const ListingData = composeComponent('Bucket.Tree.ListingData',
  RC.setPropTypes({
    urls: PT.object.isRequired,
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    children: PT.func.isRequired,
  }),
  AWS.S3.inject(),
  withData({
    params: R.pick(['s3', 'urls', 'bucket', 'path']),
    fetch: requests.bucketListing,
  }),
  ({ data: { result }, children }) => children(result));

export default composeComponent('Bucket.Tree',
  AWS.Signer.inject(),
  NamedRoutes.inject(),
  withParsedQuery,
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
    match: { params: { bucket, path } },
    location: { query: { version } },
    classes,
    signer,
    urls,
  }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        <BreadCrumbs items={getCrumbs({ bucket, path, urls })} />
        <div className={classes.spacer} />
        <CodeButton>
          {isDir(path)
            ? dirCode({ bucket, path })
            : fileCode({ bucket, path })
          }
        </CodeButton>
        {!isDir(path) && (
          <Button
            variant="outlined"
            href={signer.getSignedS3URL({ bucket, key: path, version })}
            className={classes.button}
          >
            Download file
          </Button>
        )}
      </div>

      {isDir(path)
        ? (
          <ListingData urls={urls} bucket={bucket} path={path}>
            {AsyncResult.case({
              Err: displayError(),
              _: (result) => (
                <React.Fragment>
                  <Listing
                    result={result}
                    whenEmpty={() => (
                      <Message headline="No files">
                        <Link
                          href="https://github.com/quiltdata/t4/blob/master/UserDocs.md#working-with-buckets"
                        >
                          Learn how to upload files
                        </Link>.
                      </Message>
                    )}
                  />
                  <Summary bucket={bucket} path={path} />
                </React.Fragment>
              ),
            })}
          </ListingData>
        )
        : (
          <Card>
            <CardContent>
              <ContentWindow handle={{ bucket, key: path, version }} />
            </CardContent>
          </Card>
        )
      }
    </React.Fragment>
  ));
