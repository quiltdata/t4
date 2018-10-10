import { call, put, takeLatest } from 'redux-saga/effects';

import { get } from './actions';

function* list({ s3, bucket }, path) {
  const data = yield s3.listObjectsV2({
    Bucket: bucket,
    Delimiter: '/',
    Prefix: path,
  }).promise();

  const directories = data.CommonPrefixes.map((i) => i.Prefix);
  const files = data.Contents
    .map((i) => ({
      path: i.Key,
      modified: i.LastModified,
      size: i.Size,
    }))
    // filter-out "directory-files" (files that match prefixes)
    .filter((f) => f.path !== path && !directories.includes(`${f.path}/`));

  return { files, directories };
}

function* handleGet(
  { s3, bucket },
  { payload: { path }, meta: { resolve, reject } },
) {
  try {
    const data = yield call(list, { bucket, s3 }, path);
    yield put(get.resolve(data));
    if (resolve) yield call(resolve, data);
  } catch (e) {
    yield put(get.resolve(e));
    if (reject) yield call(reject, e);
  }
}

export default function* saga({
  bucket,
  s3,
}) {
  yield takeLatest(get.type, handleGet, { s3, bucket });
}
