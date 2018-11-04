/* App selectors */
import { createSelector } from 'reselect';

import { getIn } from 'utils/immutableTools';

import { REDUX_KEY } from './constants';


export const selectSearchText = createSelector(
  getIn([REDUX_KEY, 'searchText'], ''),
  (txt) => txt,
);
