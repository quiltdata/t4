import memoize from 'lodash/memoize';
import React from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { Redirect } from 'react-router-dom';
import * as reduxHook from 'redux-react-hook';
import { createStructuredSelector } from 'reselect';
import Button from '@material-ui/core/Button';

import Error from 'components/Error';
import Working from 'components/Working';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';
import { selectLocation } from 'utils/router';

import { check } from './actions';
import { InvalidToken } from './errors';
import msg from './messages';
import * as selectors from './selectors';


const ErrorScreen = () => {
  const dispatch = reduxHook.useDispatch();
  const retry = React.useCallback(() => dispatch(check()), [dispatch]);

  return (
    <Error
      headline={<FM {...msg.wrapperFailureHeading} />}
      detail={
        <span>
          <FM {...msg.wrapperFailureDescription} />
          <Button
            variant="contained"
            color="primary"
            style={{ marginLeft: '1em' }}
            onClick={retry}
            label={<FM {...msg.wrapperFailureRetry} />}
          />
        </span>
      }
    />
  );
};

export default memoize(RT.composeHOC('Auth.Wrapper', (Component) => (props) => {
  const select = React.useMemo(() => createStructuredSelector({
    authenticated: selectors.authenticated,
    error: selectors.error,
    waiting: selectors.waiting,
    location: selectLocation,
  }), []);
  const state = reduxHook.useMappedState(select);
  const { urls } = NamedRoutes.use();

  if (state.error && !(state.error instanceof InvalidToken)) {
    return <ErrorScreen />;
  }

  // TODO: use suspense
  if (state.waiting) {
    return <Working><FM {...msg.wrapperWorking} /></Working>;
  }

  if (!state.authenticated) {
    const l = state.location;
    return <Redirect to={urls.signIn(l.pathname + l.search)} />;
  }

  return <Component {...props} />;
}));
