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
      Err: (e) => <h1>Error: {e.message}</h1>,
      Ok: R.pipe(
        // TODO: render message when thre's no packages in the bucket
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
      ),
    }, result));
