import { createActions } from 'utils/reduxTools';

export const REDUX_KEY = 'app/AWSAuth';

export const states = [
  'SIGNED_OUT',
  'SIGNING_IN',
  'SIGNED_IN',
];

export const waitingStates = [
  'SIGNING_IN',
];

export const actions = createActions(REDUX_KEY,
  'SIGN_IN',
  'SIGN_IN_RESULT',
  'SIGN_OUT',
  'AUTH_LOST',
); // eslint-disable-line function-paren-newline
