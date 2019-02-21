import * as React from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { Redirect } from 'react-router-dom';
import * as reduxHook from 'redux-react-hook';
import { createStructuredSelector } from 'reselect';

import Lifecycle from 'components/Lifecycle';
import Working from 'components/Working';
import * as Config from 'utils/Config';
import defer from 'utils/defer';
import { captureError } from 'utils/errorReporting';
import { composeComponent } from 'utils/reactTools';

import { signOut } from './actions';
import msg from './messages';
import * as selectors from './selectors';


const selector = createStructuredSelector({
  authenticated: selectors.authenticated,
  waiting: selectors.waiting,
});

export default composeComponent('Auth.SignOut', () => {
  const cfg = Config.useConfig();
  const dispatch = reduxHook.useDispatch();
  const doSignOut = React.useCallback(() => {
    const result = defer();
    dispatch(signOut(result.resolver));
    result.promise.catch(captureError);
  }, [dispatch]);
  const { waiting, authenticated } = reduxHook.useMappedState(selector);
  return (
    <React.Fragment>
      {!waiting && authenticated && <Lifecycle willMount={doSignOut} />}
      {!authenticated && <Redirect to={cfg.signOutRedirect} />}
      <Working><FM {...msg.signOutWaiting} /></Working>
    </React.Fragment>
  );
});
