import { createSelector } from 'reselect';

import { get } from 'utils/immutableTools';
import { composeComponent, RenderChildren } from 'utils/reactTools';
import { injectReducer } from 'utils/ReducerInjector';


export const REDUX_KEY = 'app/SearchProvider';

export const SET_SEARCH_TEXT = `${REDUX_KEY}/SET_SEARCH_TEXT`;

export const selectSearchText = createSelector(
  get(REDUX_KEY, ''),
  (txt) => txt,
);

export const setSearchText = (payload) => ({ type: SET_SEARCH_TEXT, payload });

export const reducer = (state = '', action) => {
  switch (action.type) {
    case SET_SEARCH_TEXT:
      return action.payload;
    default:
      return state;
  }
};

export default composeComponent('SearchProvider',
  injectReducer(REDUX_KEY, reducer),
  RenderChildren);
