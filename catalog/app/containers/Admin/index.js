import * as React from 'react';
import Typography from '@material-ui/core/Typography';

import Layout from 'components/Layout';

import Roles from './Roles';


export default () => (
  <Layout>
    <Typography variant="h4" gutterBottom>Admin</Typography>
    <Roles />
  </Layout>
);
