/* selectors for Search Results */
import { Map } from 'immutable';
import { createSelector } from 'reselect';

import { get, toJS } from 'utils/immutableTools';

import { REDUX_KEY } from './constants';


export const selectSearch = createSelector(get(REDUX_KEY, Map({})), toJS());
