import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';

import Message from './Message';
import * as packages from './packages';


export default RT.composeComponent('Bucket.PackageList',
  AWS.S3.inject(),
  NamedRoutes.inject(),
  withData({
    params: ({ s3, match: { params: { bucket } } }) => ({ s3, bucket }),
    fetch: packages.list,
  }),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      marginLeft: 'auto',
      marginRight: 'auto',
      maxWidth: 600,
    },
    card: {
      marginTop: unit,
    },
  })),
  ({ classes, data: { result }, match: { params: { bucket } }, urls }) =>
    AsyncResult.case({
      _: () => <CircularProgress />,
      Err: R.cond([
        // TODO: handle known errors:
        // access denied, cors not configured
        [R.T, (e) => <Message headline="Error">{e.message}</Message>],
      ]),
      Ok: R.ifElse(R.isEmpty,
        () => (
          <Message headline="No packages">
            <a href="https://github.com/quiltdata/t4/blob/master/UserDocs.md#publishing-a-package-to-t4">Learn how to create a package</a>.
          </Message>
        ),
        R.pipe(
          R.map(({ name, revisions: { latest: { modified } } }) => (
            <Card key={name} className={classes.card}>
              <CardContent>
                <Typography variant="h5">
                  <Link to={urls.bucketPackageDetail(bucket, name)}>
                    {name}
                  </Link>
                </Typography>
                <Typography variant="body1">
                  Updated on {modified.toLocaleString()}
                </Typography>
              </CardContent>
            </Card>
          )),
          (content) => <div className={classes.root}>{content}</div>
        )),
    }, result));
