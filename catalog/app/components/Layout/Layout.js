import * as React from 'react';
import { Grid } from 'react-bootstrap';

import Footer from 'components/Footer';
import { Pad } from 'components/LayoutHelpers';
import NavBar from 'containers/NavBar';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('Layout',
  ({ children }) => (
    <Grid fluid>
      <NavBar />
      <Pad top left right bottom>
        {children}
      </Pad>
      <Footer />
    </Grid>
  ));
