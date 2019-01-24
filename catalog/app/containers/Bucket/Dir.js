import dedent from 'dedent';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/core/styles';

import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/StyledLink';
import { composeComponent } from 'utils/reactTools';
import { getBreadCrumbs } from 'utils/s3paths';

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
          to: segPath === path ? undefined : urls.bucketDir(bucket, segPath),
        })));

const dirCode = ({ bucket, path }) => dedent`
  import t4
  b = Bucket("s3://${bucket}")
  # replace ./ to change destination directory
  b.fetch("${path}", "./")
`;

const ListingData = composeComponent('Bucket.Dir.ListingData',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    children: PT.func.isRequired,
  }),
  ({ bucket, path, children }) => (
    <NamedRoutes.Inject>
      {({ urls }) => (
        <AWS.S3.Inject>
          {(s3) => (
            <Data
              fetch={requests.bucketListing}
              params={{ s3, urls, bucket, path }}
            >
              {children}
            </Data>
          )}
        </AWS.S3.Inject>
      )}
    </NamedRoutes.Inject>
  ));

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
  ({ match: { params: { bucket, path } }, classes }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        <NamedRoutes.Inject>
          {({ urls }) => (
            <BreadCrumbs items={getCrumbs({ bucket, path, urls })} />
          )}
        </NamedRoutes.Inject>
        <div className={classes.spacer} />
        <CodeButton>{dirCode({ bucket, path })}</CodeButton>
      </div>

      <ListingData bucket={bucket} path={path}>
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
    </React.Fragment>
  ));
