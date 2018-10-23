import * as R from 'ramda';
import { call, put, takeLatest } from 'redux-saga/effects';

import AsyncResult from 'utils/AsyncResult';

import { Action } from './reducer';


const mkHandle = (bucket) => (i) => ({
  bucket,
  key: i.Key,
  modified: i.LastModified,
  size: i.Size,
  etag: i.ETag,
});

const list = async ({ s3 }, bucket, prefix) => {
  const data = await s3.listObjectsV2({
    Bucket: bucket,
    Delimiter: '/',
    Prefix: prefix,
  }).promise();

  const directories = R.pipe(
    R.pluck('Prefix'),
    R.filter((d) => d !== '../'),
    R.uniq,
  )(data.CommonPrefixes);

  const files = data.Contents
    .map(mkHandle(bucket))
    // filter-out "directory-files" (files that match prefixes)
    .filter((f) => f.key !== prefix && !directories.includes(`${f.key}/`));

  return { files, directories };
};

function* handleGet(
  { s3, bucket },
  { path, resolver: { resolve, reject } = {} },
) {
  try {
    const data = yield call(list, { s3 }, bucket, path);
    yield put(Action.GetResult(AsyncResult.Ok(data)));
    if (resolve) yield call(resolve, data);
  } catch (e) {
    // TODO: handle error
    // eslint-disable-next-line no-console
    console.log('Error listing files:', e);
    yield put(Action.GetResult(AsyncResult.Err(e)));
    if (reject) yield call(reject, e);
  }
}

const mapAction = (mapping, fn) => (...args) =>
  fn(...R.adjust(mapping, -1, args));

const takeLatestTagged = (variant, fn, ...args) =>
  // eslint-disable-next-line redux-saga/yield-effects
  takeLatest(variant.is, mapAction(variant.unbox, fn), ...args);

export default function* saga({ bucket, s3 }) {
  yield takeLatestTagged(Action.Get, handleGet, { s3, bucket });
}
