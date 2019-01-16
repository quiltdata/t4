import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import { Route, Link } from 'react-router-dom';
import { createStructuredSelector } from 'reselect';
import Button from '@material-ui/core/Button';
import { withStyles } from '@material-ui/core/styles';

import * as Auth from 'containers/AWSAuth';
import * as NamedRoutes from 'utils/NamedRoutes';
import { BaseError } from 'utils/error';
import * as RT from 'utils/reactTools';

import Message from './Message';


export class BucketError extends BaseError {}

export class AccessDenied extends BucketError {}

export class CORSError extends BucketError {}

const WhenAuth = connect(createStructuredSelector({
  authenticated: Auth.selectors.authenticated,
}))(({ authenticated, cases, args }) => cases[authenticated](...args));

const whenAuth = (cases) => (...args) => <WhenAuth {...{ cases, args }} />;

const SignIn = RT.composeComponent('Bucket.errors.SignIn',
  withStyles(({ palette }) => ({
    root: {
      '&, &:visited': {
        color: palette.primary.contrastText,
      },
    },
  })),
  ({ classes }) => (
    <NamedRoutes.Inject>
      {({ urls }) => (
        <Route>
          {({ location: l }) => (
            <Button
              component={Link}
              to={urls.signIn(l.pathname + l.search + l.hash)}
              variant="contained"
              color="primary"
              className={classes.root}
            >
              Sign In
            </Button>
          )}
        </Route>
      )}
    </NamedRoutes.Inject>
  ));

const defaultHandlers = [
  [R.is(CORSError), () => (
    <Message headline="Error">
      Seems like this bucket is not configured for T4.
      <br />
      <a
        href="https://github.com/quiltdata/t4/tree/master/deployment#pre-requisites"
      >
        Learn how to configure the bucket for T4
      </a>.
    </Message>
  )],
  [R.is(AccessDenied), whenAuth({
    true: () => (
      <Message headline="Access Denied">
        Seems like you don&apos;t have access to this bucket.
        <br />
        <a href="https://github.com/quiltdata/t4/tree/master/deployment#permissions">
          Learn about access control in T4
        </a>.
      </Message>
    ),
    false: () => (
      <Message headline="Access Denied">
        Anonymous access not allowed. Please sign in.
        <br />
        <br />
        <SignIn />
      </Message>
    ),
  })],
];

export const displayError = (pairs = []) => R.cond([
  ...defaultHandlers,
  ...pairs,
  [R.T, (e) => { throw e; }],
]);
