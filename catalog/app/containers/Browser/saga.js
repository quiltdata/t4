import { call, put, takeLatest } from 'redux-saga/effects';

import { get } from './actions';

function* getReadme({ s3, s3Bucket }, files) {
  const readmeFile = files.find(({ path: fPath }) =>
    /readme\.md$/i.test(fPath));
  if (!readmeFile) return undefined;

  const readmeObject = yield s3.getObject({
    Bucket: s3Bucket,
    Key: readmeFile.path,
  }).promise();
  return {
    file: readmeFile,
    contents: readmeObject.Body.toString('utf-8'),
  };
}

function* list({ s3, s3Bucket }, path) {
  const data = yield s3.listObjectsV2({
    Bucket: s3Bucket,
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

  return {
    files,
    directories,
    readme: yield call(getReadme, { s3, s3Bucket }, files),
  };
}

function* handleGet(
  { s3, s3Bucket },
  { payload: { path }, meta: { resolve, reject } },
) {
  try {
    const data = yield call(list, { s3Bucket, s3 }, path);
    yield put(get.resolve(data));
    if (resolve) yield call(resolve, data);
  } catch (e) {
    yield put(get.resolve(e));
    if (reject) yield call(reject, e);
  }
}

export default function* saga({
  s3Bucket,
  s3,
}) {
  yield takeLatest(get.type, handleGet, { s3, s3Bucket });
}
