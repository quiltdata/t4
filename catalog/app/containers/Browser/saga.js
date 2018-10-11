import { call, put, takeLatest } from 'redux-saga/effects';

import { get } from './actions';

const mkS3File = (bucket) => (i) => ({
  bucket,
  key: i.Key,
  modified: i.LastModified,
  size: i.Size,
  etag: i.ETag,
});

function* list({ s3 }, bucket, prefix) {
  const data = yield s3.listObjectsV2({
    Bucket: bucket,
    Delimiter: '/',
    Prefix: prefix,
  }).promise();

  const directories = data.CommonPrefixes.map((i) => i.Prefix);
  // console.log('list data', data);
  const files = data.Contents
    .map(mkS3File(bucket))
    // filter-out "directory-files" (files that match prefixes)
    .filter((f) => f.key !== prefix && !directories.includes(`${f.key}/`));

  return { files, directories };
}

function* handleGet(
  { s3, bucket },
  { payload: { path }, meta: { resolve, reject } },
) {
  try {
    const data = yield call(list, { s3 }, bucket, path);
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
