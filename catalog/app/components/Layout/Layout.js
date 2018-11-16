import * as React from 'react';

import Footer from 'components/Footer';
import { Pad } from 'components/LayoutHelpers';
import NavBar from 'containers/NavBar';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('Layout',
  ({ children }) => (
    <React.Fragment>
      <NavBar />
      <Pad top left right bottom>
        {children}
      </Pad>
      <Footer />
    </React.Fragment>
  ));
