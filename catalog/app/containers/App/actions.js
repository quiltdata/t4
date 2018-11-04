/* App actions */

import {
  SET_SEARCH_TEXT,
  START,
} from './constants';


export const setSearchText = (text) => ({ type: SET_SEARCH_TEXT, text });

export const start = () => ({ type: START });
