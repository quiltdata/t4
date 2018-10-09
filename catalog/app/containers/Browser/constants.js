import { createActions } from 'utils/reduxTools';


export const REDUX_KEY = 'app/Browser';

export const actions = createActions(REDUX_KEY,
  'GET',
  'GET_RESULT',
); // eslint-disable-line function-paren-newline
