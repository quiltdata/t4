import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/core/styles';

import Footer from 'components/Footer';
import { Pad } from 'components/LayoutHelpers';
import NavBar from 'containers/NavBar';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('Layout',
  RC.setPropTypes({
    children: PT.node,
    pre: PT.node,
  }),
  withStyles(() => ({
    root: {
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
    },
    spacer: {
      flexGrow: 1,
    },
  })),
  ({ classes, children, pre }) => (
    <div className={classes.root}>
      <NavBar />
      {!!pre && pre}
      <Pad top left right bottom>
        {children}
      </Pad>
      <div className={classes.spacer} />
      <Footer />
    </div>
  ));
