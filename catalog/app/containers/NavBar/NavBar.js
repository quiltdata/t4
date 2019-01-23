import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import { Link, Route } from 'react-router-dom';
import * as RC from 'recompose';
import { createStructuredSelector } from 'reselect';
import AppBar from '@material-ui/core/AppBar';
import Button from '@material-ui/core/Button';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import Menu from '@material-ui/core/Menu';
import MenuItem from '@material-ui/core/MenuItem';
import Toolbar from '@material-ui/core/Toolbar';
import { withStyles } from '@material-ui/core/styles';

import * as authSelectors from 'containers/AWSAuth/selectors';
import * as NamedRoutes from 'utils/NamedRoutes';
import { composeComponent } from 'utils/reactTools';

import logo from 'img/logo/horizontal-white.png';

import BucketControls from './BucketControls';


const Logo = composeComponent('NavBar.Logo',
  NamedRoutes.inject(),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      height: unit * 4.5,
      marginRight: unit * 2,
    },
    img: {
      height: '100%',
    },
  })),
  ({ classes, urls }) => (
    <Link className={classes.root} to={urls.home()}>
      <img className={classes.img} alt="Quilt logo" src={logo} />
    </Link>
  ));

const Item = composeComponent('NavBar.MenuItem',
  RC.withProps({ component: Link }),
  MenuItem);

const NavMenu = composeComponent('NavBar.Menu',
  NamedRoutes.inject(),
  RC.withStateHandlers({
    anchor: null,
  }, {
    open: () => (evt) => ({ anchor: evt.target }),
    close: () => () => ({ anchor: null }),
  }),
  ({ anchor, open, close, urls }) => (
    <div>
      <Button
        variant="text"
        color="inherit"
        onClick={open}
      >
        AWS IAM <Icon>expand_more</Icon>
      </Button>
      <Menu
        anchorEl={anchor}
        open={!!anchor}
        onClose={close}
      >
        <Item to={urls.signOut()} onClick={close}>Sign Out</Item>
      </Menu>
    </div>
  ));

const SignIn = composeComponent('NavBar.SignIn',
  RC.setPropTypes({
    error: PT.object,
    waiting: PT.bool.isRequired,
  }),
  NamedRoutes.inject(),
  withStyles(({ spacing: { unit } }) => ({
    icon: {
      marginRight: unit,
    },
  })),
  ({ error, waiting, urls, classes }) => {
    if (waiting) {
      return <CircularProgress color="inherit" />;
    }
    return (
      <React.Fragment>
        {error && (
          <Icon
            title={`${error.message}\n${JSON.stringify(error)}`}
            className={classes.icon}
          >
            error_outline
          </Icon>
        )}
        <Button
          component={Link}
          to={urls.signIn()}
          variant="text"
          color="inherit"
        >
          Sign In
        </Button>
      </React.Fragment>
    );
  });

export const Container = composeComponent('NavBar.Container',
  withStyles(({ palette }) => ({
    root: {
      backgroundColor: palette.primary.dark,
      color: palette.getContrastText(palette.primary.dark),
    },
  })),
  ({ classes, children }) => (
    <AppBar className={classes.root} color="default" position="static">
      <Toolbar>
        <Logo />
        {children}
      </Toolbar>
    </AppBar>
  ));

const Spacer = composeComponent('NavBar.Spacer',
  withStyles(() => ({
    root: {
      flexGrow: 1,
    },
  })),
  ({ classes }) => <div className={classes.root} />);

const whenNot = (path, fn) => (
  <Route path={path} exact>
    {({ match }) => !match && fn()}
  </Route>
);

export const NavBar = composeComponent('NavBar',
  connect(createStructuredSelector(
    R.pick(['error', 'waiting', 'authenticated'], authSelectors)
  ), undefined, undefined, { pure: false }),
  NamedRoutes.inject(),
  ({ paths, error, waiting, authenticated }) => (
    <Container>
      {whenNot(paths.signIn, () => <BucketControls />)}
      <Spacer />
      {authenticated
        ? <NavMenu />
        : whenNot(paths.signIn, () =>
          <SignIn error={error} waiting={waiting} />)
      }
    </Container>
  ));

export default NavBar;
