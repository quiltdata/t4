/* App sagas */
import { put } from 'redux-saga/effects';

import { start } from './actions';


export default function* () {
  yield put(start());
}
