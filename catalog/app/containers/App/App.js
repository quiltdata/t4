import * as R from 'ramda';
import * as React from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';

import {
  SignIn,
  SignOut,
  requireAuth,
} from 'containers/AWSAuth';
import * as Bucket from 'containers/Bucket';
import HomePage from 'containers/HomePage/Loadable';
import NotFoundPage from 'containers/NotFoundPage/Loadable';
import * as NamedRoutes from 'utils/NamedRoutes';
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

const renderRoutes = (pairs, fallback) => (
  <Switch>
    {pairs.map(([path, component]) =>
      <Route exact key={path} {...{ path, component }} />)}
    <Route component={fallback} />
  </Switch>
);

export default composeComponent('App',
  injectSaga(REDUX_KEY, saga),
  NamedRoutes.inject(),
  ({ paths, urls }) =>
    renderRoutes([
      [paths.home, ProtectedHome],
      [paths.signIn, SignIn],
      ['/login', redirectTo(urls.signIn())],
      [paths.signOut, SignOut],
      [paths.bucketRoot, requireAuth(Bucket.Overview)],
      [paths.bucketTree, requireAuth(Bucket.Tree)],
      [paths.bucketSearch, requireAuth(Bucket.Search)],
      [paths.bucketPackageList, requireAuth(Bucket.PackageList)],
      [paths.bucketPackageDetail, requireAuth(Bucket.PackageDetail)],
    ], ProtectedNotFound));
