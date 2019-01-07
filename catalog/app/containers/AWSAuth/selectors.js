import { Map } from 'immutable';
import id from 'lodash/identity';
import { createSelector } from 'reselect';

import { get, getIn, toJS } from 'utils/immutableTools';

import { REDUX_KEY, waitingStates } from './constants';

export const domain = createSelector(get(REDUX_KEY, Map({})), toJS());

export const state = createSelector(getIn([REDUX_KEY, 'state']), id);

export const waiting = createSelector(state, (s) => waitingStates.includes(s));

export const error = createSelector(getIn([REDUX_KEY, 'error']), id);

export const credentials = createSelector(getIn([REDUX_KEY, 'credentials']), toJS());

export const authenticated = createSelector(credentials, state,
  (c, s) => !!c && s === 'SIGNED_IN');
