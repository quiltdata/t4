import { actionCreator } from 'utils/reduxTools';

import { actions } from './constants';


/**
 * Create a SIGN_IN action.
 *
 * @param {{username: string, password: string}} credentials
 *
 * @param {{resolve: function, reject: function}} resolver
 *
 * @returns {Action}
 */
export const signIn = actionCreator(actions.SIGN_IN, (credentials, resolver) => ({
  payload: credentials,
  meta: { ...resolver },
}));

/**
 * Create a SIGN_IN_RESULT action.
 *
 * @param {{tokens: Object, user: Object}|Error} result
 *   Either an error or an object containing tokens and user data.
 *   If error, action.error is true.
 *
 * @returns {Action}
 */
signIn.resolve = actionCreator(actions.SIGN_IN_RESULT, (payload) => ({
  error: payload instanceof Error,
  payload,
}));

/**
 * Create a SIGN_OUT action.
 *
 * @param {{ resolve: function, reject: function }} resolver
 *
 * @returns {Action}
 */
export const signOut = actionCreator(actions.SIGN_OUT);

/**
 * Create an AUTH_LOST action.
 *
 * @param {Error} error
 *   Error that caused authentication loss.
 *
 * @returns {Action}
 */
export const authLost = actionCreator(actions.AUTH_LOST, (payload) => ({
  payload,
}));
