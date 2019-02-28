import * as React from 'react';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import Layout from 'components/Layout';

import Roles from './Roles';
import Users from './Users';


export default withStyles((t) => ({
  section: {
    marginTop: t.spacing.unit * 2,
  },
}))(({ classes }) => (
  <Layout>
    <div className={classes.section}>
      <Typography variant="h4">Admin</Typography>
    </div>
    <div className={classes.section}>
      <Users />
    </div>
    <div className={classes.section}>
      <Roles />
    </div>
  </Layout>
));
