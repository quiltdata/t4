import * as React from 'react';

import Error from 'components/Error';
import Layout from 'components/Layout';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('NotFoundPage',
  () => (
    <Layout>
      <Error headline="Nothing here" detail="Do you need to log in?" />
    </Layout>
  ));
