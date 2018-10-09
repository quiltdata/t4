import { Map } from 'immutable';

import {
  handleActions,
  handleResult,
  combine,
  withInitialState,
  unset,
} from 'utils/reduxTools';

import { actions } from './constants';


const initial = Map({
});

export default withInitialState(initial, handleActions({
  [actions.GET]: combine({
    state: 'FETCHING',
    path: (p) => p.path,
    result: unset,
  }),
  // TODO: check if response corresponds to the current state (path)
  [actions.GET_RESULT]: handleResult({
    resolve: combine({
      state: 'READY',
      result: (p) => p,
    }),
    reject: combine({
      state: 'ERROR',
      result: (p) => p,
    }),
  }),
}));
