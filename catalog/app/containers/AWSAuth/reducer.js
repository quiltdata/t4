import id from 'lodash/identity';
import { fromJS } from 'immutable';

import { get } from 'utils/immutableTools';
import {
  withInitialState,
  handleActions,
  handleResult,
  handleTransitions,
  combine,
  unset,
} from 'utils/reduxTools';

import { actions } from './constants';


const initial = {
  state: 'SIGNED_OUT',
};

export default withInitialState(fromJS(initial), handleTransitions(get('state'), {
  SIGNED_OUT: handleActions({
    [actions.SIGN_IN]: combine({
      state: 'SIGNING_IN',
      credentials: (p) => fromJS(p),
      error: unset,
    }),
  }),
  SIGNING_IN: handleActions({
    [actions.SIGN_IN_RESULT]: handleResult({
      resolve: combine({
        state: 'SIGNED_IN',
      }),
      reject: combine({
        state: 'SIGNED_OUT',
      }),
    }),
  }),
  SIGNED_IN: handleActions({
    [actions.SIGN_OUT]: combine({
      state: 'SIGNED_OUT',
      credentials: unset,
    }),
    [actions.AUTH_LOST]: combine({
      state: 'SIGNED_OUT',
      credentials: unset,
      error: id,
    }),
  }),
}));
