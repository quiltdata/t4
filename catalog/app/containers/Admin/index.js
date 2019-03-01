import * as React from 'react';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import Layout from 'components/Layout';
import * as APIConnector from 'utils/APIConnector';
import * as Cache from 'utils/ResourceCache';

import Roles from './Roles';
import Users from './Users';
import * as data from './data';


export default withStyles((t) => ({
  section: {
    marginTop: t.spacing.unit * 2,
  },
}))(({ classes }) => {
  const req = APIConnector.use();
  const users = Cache.useData(data.UsersResource, { req });
  const roles = Cache.useData(data.RolesResource, { req });
  return (
    <Layout>
      <div className={classes.section}>
        <Typography variant="h4">Admin</Typography>
      </div>
      <div className={classes.section}>
        <Users users={users} roles={roles} />
      </div>
      <div className={classes.section}>
        <Roles roles={roles} />
      </div>
    </Layout>
  );
});
