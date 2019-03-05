import * as R from 'ramda';
import * as React from 'react';
import { Switch, Route, Redirect } from 'react-router-dom';

import Admin from 'containers/Admin';
import * as Auth from 'containers/Auth';
import Bucket from 'containers/Bucket';
import HomePage from 'containers/HomePage/Loadable';
import { CatchNotFound, ThrowNotFound } from 'containers/NotFoundPage';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import { useLocation } from 'utils/router';


// eslint-disable-next-line react/prop-types
const redirectTo = (path) => ({ location: { search } }) =>
  <Redirect to={`${path}${search}`} />;

const useAuth = () => {
  const { alwaysRequiresAuth } = Config.useConfig();
  return React.useMemo(
    () => alwaysRequiresAuth ? Auth.requireAuth() : R.identity,
    [alwaysRequiresAuth],
  );
};

const requireAdmin = Auth.requireAuth({
  authorizedSelector: Auth.selectors.isAdmin,
});

export default () => {
  const protect = useAuth();
  const { paths, urls } = NamedRoutes.use();
  const l = useLocation();

  return (
    <CatchNotFound id={`${l.pathname}${l.search}${l.hash}`}>
      <Switch>
        <Route path={paths.home} component={protect(HomePage)} exact />

        <Route path={paths.signIn} component={Auth.SignIn} exact />
        <Route path="/login" component={redirectTo(urls.signIn())} exact />
        <Route path={paths.signOut} component={Auth.SignOut} exact />
        <Route path={paths.signUp} component={Auth.SignUp} exact />
        <Route path={paths.passReset} component={Auth.PassReset} exact />
        <Route path={paths.passChange} component={Auth.PassChange} exact />
        <Route path={paths.code} component={protect(Auth.Code)} exact />
        <Route path={paths.activationError} component={Auth.ActivationError} exact />

        <Route path={paths.admin} component={requireAdmin(Admin)} exact />

        <Route path={paths.bucketRoot} component={protect(Bucket)} />

        <Route component={protect(ThrowNotFound)} />
      </Switch>
    </CatchNotFound>
  );
};
