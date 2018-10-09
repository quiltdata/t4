import { actionCreator } from 'utils/reduxTools';

import { actions } from './constants';


export const get = actionCreator(actions.GET, (path, resolver) => ({
  payload: { path },
  meta: { ...resolver },
}));

get.resolve = actionCreator(actions.GET_RESULT, (payload) => ({
  error: payload instanceof Error,
  payload,
}));
