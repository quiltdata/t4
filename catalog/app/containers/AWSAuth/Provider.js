import { fromJS } from 'immutable';
import pick from 'lodash/fp/pick';
import PT from 'prop-types';
import { Fragment } from 'react';
import { injectIntl } from 'react-intl';
import { connect } from 'react-redux';
import { defaultProps, mapProps, withHandlers, setPropTypes } from 'recompose';

import { push as notify } from 'containers/Notifications/actions';
import { composeComponent } from 'utils/reactTools';
import { injectReducer } from 'utils/ReducerInjector';
import { injectSaga } from 'utils/SagaInjector';

import { REDUX_KEY } from './constants';
import msg from './messages';
import reducer from './reducer';
import saga from './saga';


/**
 * Provider component for the AWS / IAM authentication system.
 */
export default composeComponent('AWSAuth.Provider',
  setPropTypes({
    /**
     * Storage instance used to persist tokens and user data.
     */
    storage: PT.shape({
      set: PT.func.isRequired,
      remove: PT.func.isRequired,
      load: PT.func.isRequired,
    }),
    /**
     * Bucket used to verify the credentials.
     */
    testBucket: PT.string,
    /**
     * Where to redirect after sign-out.
     */
    signOutRedirect: PT.string,
    /**
     * Where to redirect after sign-in by default (if no `next` param provided).
     */
    signInRedirect: PT.string,
  }),
  defaultProps({
    signOutRedirect: '/',
    signInRedirect: '/',
  }),
  injectIntl,
  connect(undefined, undefined, undefined, { pure: false }),
  withHandlers({
    storeCredentials: ({ storage }) => (credentials) =>
      storage.set('credentials', credentials),
    forgetCredentials: ({ storage }) => () => storage.remove('credentials'),
    onAuthLost: ({ intl, dispatch }) => () => {
      dispatch(notify(intl.formatMessage(msg.notificationAuthLost)));
    },
  }),
  injectReducer(REDUX_KEY, reducer, ({ storage, signInRedirect, signOutRedirect }) =>
    fromJS(storage.load())
      .filter(Boolean)
      .update((s) =>
        s.set('state', s.get('credentials') ? 'SIGNED_IN' : 'SIGNED_OUT'))
      .set('signInRedirect', signInRedirect)
      .set('signOutRedirect', signOutRedirect)),
  injectSaga(REDUX_KEY, saga),
  mapProps(pick(['children'])),
  Fragment);
