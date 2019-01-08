import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Icon from '@material-ui/core/Icon';
import { withStyles } from '@material-ui/core/styles';

import * as BucketConfig from 'utils/BucketConfig';
import * as RT from 'utils/reactTools';

import BucketSelect from './BucketSelect';
import Search from './Search';


const BucketDisplay = RT.composeComponent('NavBar.BucketControls.BucketDisplay',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    select: PT.func.isRequired,
  }),
  withStyles(() => ({
    root: {
      textTransform: 'none !important',
    },
    s3: {
      opacity: 0.7,
    },
    bucket: {
      maxWidth: 320,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
  })),
  ({ classes, bucket, select }) => (
    <Button
      color="inherit"
      className={classes.root}
      onClick={select}
    >
      <span className={classes.s3}>s3://</span>
      <span className={classes.bucket}>{bucket}</span>
      <Icon>expand_more</Icon>
    </Button>
  ));

const dispatchOn = (prop, cases) => ({ [prop]: value, ...props }) =>
  cases[value](props);

const BucketDisplaySelect = RT.composeComponent('NavBar.BucketControls.BucketDisplaySelect',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
  }),
  RC.withStateHandlers({
    selecting: false,
  }, {
    select: () => () => ({ selecting: true }),
    cancel: () => () => ({ selecting: false }),
  }),
  dispatchOn('selecting', {
    // eslint-disable-next-line react/prop-types
    true: ({ cancel }) => <BucketSelect autoFocus cancel={cancel} />,
    // eslint-disable-next-line react/prop-types
    false: ({ bucket, select }) =>
      <BucketDisplay bucket={bucket} select={select} />,
  }));

export default RT.composeComponent('NavBar.BucketControls',
  withStyles(() => ({
    root: {
      alignItems: 'center',
      display: 'flex',
    },
  })),
  ({ classes }) => (
    <div className={classes.root}>
      <BucketConfig.WithCurrentBucket>
        {(bucket) => bucket
          ? (
            <React.Fragment>
              <BucketDisplaySelect bucket={bucket} />
              <Search />
            </React.Fragment>
          )
          : <BucketSelect />
        }
      </BucketConfig.WithCurrentBucket>
    </div>
  ));
