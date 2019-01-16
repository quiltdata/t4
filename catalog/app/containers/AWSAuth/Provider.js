import { fromJS } from 'immutable';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { injectIntl } from 'react-intl';
import { connect } from 'react-redux';
import * as RC from 'recompose';

import { push as notify } from 'containers/Notifications/actions';
import * as Config from 'utils/Config';
import * as ReducerInjector from 'utils/ReducerInjector';
import * as SagaInjector from 'utils/SagaInjector';
import * as Wait from 'utils/Wait';
import * as RT from 'utils/reactTools';
import { withInitialState } from 'utils/reduxTools';

import { REDUX_KEY } from './constants';
import msg from './messages';
import reducer from './reducer';
import saga from './saga';


const StorageShape = PT.shape({
  set: PT.func.isRequired,
  remove: PT.func.isRequired,
  load: PT.func.isRequired,
});

const Handlers = RT.composeComponent('AWSAuth.Provider.Handlers',
  RC.setPropTypes({
    storage: StorageShape.isRequired,
  }),
  injectIntl,
  connect(undefined, undefined, undefined, { pure: false }),
  RC.withHandlers({
    storeCredentials: ({ storage }) => (credentials) =>
      storage.set('credentials', credentials),
    forgetCredentials: ({ storage }) => () => storage.remove('credentials'),
    onAuthLost: ({ intl, dispatch }) => () => {
      dispatch(notify(intl.formatMessage(msg.notificationAuthLost)));
    },
  }),
  ({ children, ...props }) =>
    R.pipe(
      R.pick(['storeCredentials', 'forgetCredentials', 'onAuthLost']),
      children,
    )(props));

/**
 * Provider component for the AWS / IAM authentication system.
 */
export default RT.composeComponent('AWSAuth.Provider',
  RC.setPropTypes({
    /**
     * Storage instance used to persist tokens and user data.
     */
    storage: StorageShape.isRequired,
  }),
  ({ children, storage }) => (
    <Config.Inject>
      {Wait.wait(({ defaultBucket, guestCredentials }) => (
        <Handlers storage={storage}>
          {(handlers) => {
            const init =
              fromJS(storage.load())
                .filter(Boolean)
                .set('guestCredentials', guestCredentials)
                .update((s) =>
                  s.set('state', s.get('credentials') ? 'SIGNED_IN' : 'SIGNED_OUT'));

            return (
              <ReducerInjector.Inject
                mount={REDUX_KEY}
                reducer={withInitialState(init, reducer)}
              >
                <SagaInjector.Inject
                  name={REDUX_KEY}
                  saga={saga}
                  args={[{ ...handlers, testBucket: defaultBucket }]}
                >
                  {children}
                </SagaInjector.Inject>
              </ReducerInjector.Inject>
            );
          }}
        </Handlers>
      ))}
    </Config.Inject>
  ));
