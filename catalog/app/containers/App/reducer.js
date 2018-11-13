/* App reducer */
import {
  SET_SEARCH_TEXT,
  initialState,
} from './constants';


export default (state = initialState, action) => {
  switch (action.type) {
    case SET_SEARCH_TEXT:
      return state.setIn(['searchText'], action.text);
    default:
      return state;
  }
};
