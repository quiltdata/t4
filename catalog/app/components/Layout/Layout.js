import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/core/styles';

import Footer from 'components/Footer';
import { Pad } from 'components/LayoutHelpers';
import * as NavBar from 'containers/NavBar';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('Layout',
  RC.setPropTypes({
    children: PT.node,
    pre: PT.node,
    bare: PT.bool,
  }),
  withStyles(({ palette }) => ({
    root: {
      background: palette.background.default,
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
    },
    spacer: {
      flexGrow: 1,
    },
  })),
  ({ bare, classes, children, pre }) => (
    <div className={classes.root}>
      {bare ? <NavBar.Container /> : <NavBar.NavBar />}
      {!!pre && pre}
      <Pad top left right bottom>
        {children}
      </Pad>
      <div className={classes.spacer} />
      <Footer />
    </div>
  ));
