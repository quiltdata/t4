/* App */
import id from 'lodash/identity';
import React from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';

import CoreLF from 'components/CoreLF';
import Footer from 'components/Footer';
import { Pad } from 'components/LayoutHelpers';
import {
  SignIn,
  SignOut,
  requireAuth,
} from 'containers/AWSAuth';
import AuthBar from 'containers/AuthBar';
import Browser from 'containers/Browser';
import HomePage from 'containers/HomePage/Loadable';
import NotFoundPage from 'containers/NotFoundPage/Loadable';
import Notifications from 'containers/Notifications';
import SearchResults from 'containers/SearchResults/Loadable';
import { injectReducer } from 'utils/ReducerInjector';
import { injectSaga } from 'utils/SagaInjector';
import { composeComponent } from 'utils/reactTools';

import config from 'constants/config';

import { REDUX_KEY } from './constants';
import reducer from './reducer';
import saga from './saga';

const requireAuthIfConfigured = config.alwaysRequiresAuth ? requireAuth : id;

const ProtectedHome = requireAuthIfConfigured(HomePage);
const ProtectedNotFound = requireAuthIfConfigured(NotFoundPage);

// eslint-disable-next-line react/prop-types
const redirectTo = (path) => ({ location: { search } }) =>
  <Redirect to={`${path}${search}`} />;

export default composeComponent('App',
  injectReducer(REDUX_KEY, reducer),
  injectSaga(REDUX_KEY, saga),
  () => (
    <CoreLF>
      <Route path="/signin" exact>
        {({ match }) => <AuthBar showUserMenu={!match} />}
      </Route>
      <Pad top left right bottom>
        <Switch>
          <Route path="/" exact component={ProtectedHome} />
          <Route path="/search" exact component={requireAuth(SearchResults)} />
          <Route path="/browse/:path(.*)?" exact component={requireAuth(Browser)} />

          <Route path="/signin" exact component={SignIn} />
          <Route path="/login" exact render={redirectTo('/signin')} />
          <Route path="/signout" exact component={SignOut} />

          <Route path="" component={ProtectedNotFound} />
        </Switch>
      </Pad>
      <Footer />
      <Notifications />
    </CoreLF>
  ));
