import * as R from 'ramda';
import * as React from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';

import {
  SignIn,
  SignOut,
  requireAuth,
} from 'containers/AWSAuth';
import Bucket from 'containers/Bucket';
import HomePage from 'containers/HomePage/Loadable';
import { CatchNotFound, ThrowNotFound } from 'containers/NotFoundPage';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Wait from 'utils/Wait';
import * as RT from 'utils/reactTools';


// eslint-disable-next-line react/prop-types
const redirectTo = (path) => ({ location: { search } }) =>
  <Redirect to={`${path}${search}`} />;

export default RT.composeComponent('App', () => (
  <Config.Inject>
    {Wait.wait((config) => {
      const protect = config.alwaysRequiresAuth ? requireAuth : R.identity;

      return (
        <Route>
          {({ location: l }) => (
            <CatchNotFound id={`${l.pathname}${l.search}${l.hash}`}>
              <NamedRoutes.Inject>
                {({ paths, urls }) => (
                  <Switch>
                    <Route
                      path={paths.home}
                      component={protect(HomePage)}
                      exact
                    />
                    <Route
                      path={paths.signIn}
                      component={SignIn}
                      exact
                    />
                    <Route
                      path="/login"
                      component={redirectTo(urls.signIn())}
                      exact
                    />
                    <Route
                      path={paths.signOut}
                      component={SignOut}
                      exact
                    />
                    <Route
                      path={paths.bucketRoot}
                      component={protect(Bucket)}
                    />
                    <Route
                      component={protect(ThrowNotFound)}
                    />
                  </Switch>
                )}
              </NamedRoutes.Inject>
            </CatchNotFound>
          )}
        </Route>
      );
    })}
  </Config.Inject>
));
