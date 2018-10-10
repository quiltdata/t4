import { createActions } from 'utils/reduxTools';


export const REDUX_KEY = 'app/Browser';

export const actions = createActions(REDUX_KEY,
  'GET',
  'GET_RESULT',
); // eslint-disable-line function-paren-newline

export const README_RE = /^readme\.md$/i;
export const SUMMARY_RE = /^quilt_summarize\.json$/i;

export const EXPIRATION = 5 * 60; // in seconds
