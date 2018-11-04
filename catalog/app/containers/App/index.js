import * as R from 'ramda';
import * as React from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';

import {
  SignIn,
  SignOut,
  requireAuth,
} from 'containers/AWSAuth';
import Browser from 'containers/Browser';
import HomePage from 'containers/HomePage/Loadable';
import NotFoundPage from 'containers/NotFoundPage/Loadable';
import SearchResults from 'containers/SearchResults/Loadable';
import { injectSaga } from 'utils/SagaInjector';
import { composeComponent } from 'utils/reactTools';

import config from 'constants/config';

import { REDUX_KEY } from './constants';
import saga from './saga';

const requireAuthIfConfigured = config.alwaysRequiresAuth ? requireAuth : R.identity;

const ProtectedHome = requireAuthIfConfigured(HomePage);
const ProtectedNotFound = requireAuthIfConfigured(NotFoundPage);

// eslint-disable-next-line react/prop-types
const redirectTo = (path) => ({ location: { search } }) =>
  <Redirect to={`${path}${search}`} />;

export default composeComponent('App',
  injectSaga(REDUX_KEY, saga),
  () => (
    <Switch>
      <Route path="/" exact component={ProtectedHome} />
      <Route path="/search" exact component={requireAuth(SearchResults)} />
      <Route path="/browse/:path(.*)?" exact component={requireAuth(Browser)} />
      <Route path="/signin" exact component={SignIn} />
      <Route path="/login" exact render={redirectTo('/signin')} />
      <Route path="/signout" exact component={SignOut} />
      <Route component={ProtectedNotFound} />
    </Switch>
  ));
