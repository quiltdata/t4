import * as React from 'react';
import CircularProgress from '@material-ui/core/CircularProgress';
import { withStyles } from '@material-ui/styles';

import Delay from 'utils/Delay';
import * as RT from 'utils/reactTools';


export default RT.composeComponent('App.Placeholder',
  withStyles(() => ({
    root: {
      alignItems: 'center',
      display: 'flex',
      justifyContent: 'center',
      minHeight: '100vh',
    },
  })),
  ({ classes }) => (
    <div className={classes.root}>
      <Delay>{() => <CircularProgress size={120} />}</Delay>
    </div>
  ));

