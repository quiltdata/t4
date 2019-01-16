import { Map } from 'immutable';
import id from 'lodash/identity';
import { createSelector } from 'reselect';

import { get, getIn, toJS } from 'utils/immutableTools';

import { REDUX_KEY, waitingStates } from './constants';

export const domain = createSelector(get(REDUX_KEY, Map({})), toJS());

export const state = createSelector(getIn([REDUX_KEY, 'state']), id);

export const waiting = createSelector(state, (s) => waitingStates.includes(s));

export const error = createSelector(getIn([REDUX_KEY, 'error']), id);

export const credentials = createSelector(domain,
  (s) => s.credentials || s.guestCredentials);

export const authenticated = createSelector(state, (s) => s === 'SIGNED_IN');
