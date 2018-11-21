import * as R from 'ramda';
import * as React from 'react';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/PlainLink';
import * as RT from 'utils/reactTools';

import * as packages from './packages';


const Field = RT.composeComponent('Bucket.PackageDetail.Field',
  withStyles(({ typography }) => ({
    root: {
      display: 'flex',
    },
    label: {
      fontWeight: typography.fontWeightMedium,
      width: 80,
    },
    value: {
    },
  })),
  ({ classes, label, children }) => (
    <Typography
      variant="body1"
      className={classes.root}
    >
      <span className={classes.label}>{label}</span>
      <span className={classes.value}>{children}</span>
    </Typography>
  ));

export default RT.composeComponent('Bucket.PackageDetail',
  AWS.S3.inject(),
  withData({
    params: ({ s3, match: { params: { bucket, name } } }) =>
      ({ s3, bucket, name }),
    fetch: packages.getRevisions,
  }),
  NamedRoutes.inject(),
  withStyles(({ spacing: { unit }, palette }) => ({
    card: {
      marginTop: unit,
    },
    link: {
      display: 'block',
      '&:hover': {
        background: palette.action.hover,
      },
    },
  })),
  ({
    urls,
    classes,
    match: { params: { bucket, name } },
    data: { result },
  }) => (
    <React.Fragment>
      <Typography variant="h4">
        {name}: revisions
      </Typography>
      {AsyncResult.case({
        _: () => <CircularProgress />,
        Err: (e) => <h1>Error: {e.message}</h1>,
        Ok: R.map(({ id, hash, modified, info }) => id !== 'latest' && (
          <Card key={id} className={classes.card}>
            <CardContent
              component={Link}
              className={classes.link}
              to={urls.bucketPackageTree(bucket, name, id)}
            >
              <Field label="Message:">{info.commit_message || '<empty>'}</Field>
              <Field label="Date:">{modified.toLocaleString()}</Field>
              <Field label="Hash:">{hash}</Field>
            </CardContent>
          </Card>
        )),
      }, result)}
    </React.Fragment>
  ));
