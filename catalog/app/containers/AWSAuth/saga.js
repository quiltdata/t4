import S3 from 'aws-sdk/clients/s3';
import { call, put, fork, takeEvery } from 'redux-saga/effects';

import * as actions from './actions';
import * as errors from './errors';


/**
 * Verify credentials by trying to list objects in the test bucket.
 * Throw InvalidCredentials if access is denied.
 *
 * @param {string} testBucket
 * @param {object} credentials
 *
 * @throws {InvalidCredentials}
 */
function* verifyCredentials(testBucket, credentials) {
  try {
    const s3 = new S3({ apiVersion: '2006-03-01', ...credentials });
    yield s3.listObjectsV2({ Bucket: testBucket, MaxKeys: 1 }).promise();
  } catch (e) {
    if (e.name === 'InvalidAccessKeyId') throw new errors.InvalidCredentials();
    throw e;
  }
}

/**
 * Handle SIGN_IN action.
 * Make a sign-in request using the given credentials,
 * then request the user data using received tokens.
 * Finally, store the tokens and user data and dispatch a SIGN_IN_RESULT action.
 * Call resolve or reject callback.
 *
 * @param {Object} options
 * @param {function} options.storeCredentials
 * @param {function} options.testBucket
 *
 * @param {Action} action
 */
function* handleSignIn(
  { storeCredentials, testBucket },
  { payload: credentials, meta: { resolve, reject } },
) {
  try {
    yield call(verifyCredentials, testBucket, credentials);
    yield fork(storeCredentials, credentials);
    yield put(actions.signIn.resolve());
    /* istanbul ignore else */
    if (resolve) yield call(resolve);
  } catch (e) {
    yield put(actions.signIn.resolve(e));
    /* istanbul ignore else */
    if (reject) yield call(reject, e);
  }
}

/**
 * Handle SIGN_OUT action.
 *
 * @param {Object} options
 * @param {function} options.forgetTokens
 * @param {function} options.forgetUser
 *
 * @param {Action} action
 */
function* handleSignOut({ forgetCredentials }) {
  yield fork(forgetCredentials);
}

/**
 * Handle AUTH_LOST action.
 *
 * @param {Object} options
 * @param {function} options.onAuthLost
 * @param {Action} action
 */
function* handleAuthLost({ forgetCredentials, onAuthLost }, { payload: err }) {
  yield fork(forgetCredentials);
  yield call(onAuthLost, err);
}

/**
 * Main AWS Auth saga.
 * Handles auth actions and fires CHECK action on specified condition.
 *
 * @param {Object} options
 * @param {function} options.storeCredentils
 * @param {function} options.forgetCredentials
 * @param {string} options.testBucket
 * @param {function} options.onAuthLost
 */
export default function* ({
  storeCredentials,
  forgetCredentials,
  testBucket,
  onAuthLost,
}) {
  yield takeEvery(actions.signIn.type, handleSignIn,
    { storeCredentials, testBucket });
  yield takeEvery(actions.signOut.type, handleSignOut,
    { forgetCredentials });
  yield takeEvery(actions.authLost.type, handleAuthLost,
    { forgetCredentials, onAuthLost });
}
