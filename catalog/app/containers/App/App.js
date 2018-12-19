import * as R from 'ramda';
import * as React from 'react';
import { Switch, Route, Redirect, withRouter } from 'react-router-dom';

import {
  SignIn,
  SignOut,
  requireAuth,
} from 'containers/AWSAuth';
import Bucket from 'containers/Bucket';
import HomePage from 'containers/HomePage/Loadable';
import { CatchNotFound, ThrowNotFound } from 'containers/NotFoundPage';
import * as NamedRoutes from 'utils/NamedRoutes';
import { injectSaga } from 'utils/SagaInjector';
import { composeComponent } from 'utils/reactTools';

import config from 'constants/config';

import { REDUX_KEY } from './constants';
import saga from './saga';


const requireAuthIfConfigured = config.alwaysRequiresAuth ? requireAuth : R.identity;

const ProtectedHome = requireAuthIfConfigured(HomePage);
const ProtectedNotFound = requireAuthIfConfigured(ThrowNotFound);

// eslint-disable-next-line react/prop-types
const redirectTo = (path) => ({ location: { search } }) =>
  <Redirect to={`${path}${search}`} />;

export default composeComponent('App',
  injectSaga(REDUX_KEY, saga),
  NamedRoutes.inject(),
  withRouter,
  ({ location: l, paths, urls }) => (
    <CatchNotFound id={`${l.pathname}${l.search}${l.hash}`}>
      <Switch>
        <Route path={paths.home} component={ProtectedHome} exact />
        <Route path={paths.signIn} component={SignIn} exact />
        <Route path="/login" component={redirectTo(urls.signIn())} exact />
        <Route path={paths.signOut} component={SignOut} exact />
        <Route path={paths.bucketRoot} component={requireAuth(Bucket)} />
        <Route component={ProtectedNotFound} />
      </Switch>
    </CatchNotFound>
  ));
