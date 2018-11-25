import * as R from 'ramda';


const PACKAGES_PREFIX = '.quilt/named_packages/';
const MANIFESTS_PREFIX = '.quilt/packages/';

export const list = async ({ s3, bucket }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Prefix: PACKAGES_PREFIX,
    })
    .promise()
    .then(R.pipe(
      R.prop('Contents'),
      R.map(({ Key, LastModified }) => {
        const i = Key.lastIndexOf('/');
        const name = Key.substring(PACKAGES_PREFIX.length, i);
        const revision = Key.substring(i + 1);
        return { name, revision, key: Key, modified: LastModified };
      }),
      R.reduce((acc, { name, revision, key, modified }) => ({
        ...acc,
        [name]: { ...acc[name], [revision]: { key, modified } },
      }), {}),
      R.toPairs,
      R.map(([name, revisions]) => ({ name, revisions })),
      R.filter(({ name }) => name.includes('/')),
    ));

const loadRevisionHash = ({ s3, bucket }) => async (key) =>
  s3
    .getObject({ Bucket: bucket, Key: key })
    .promise()
    .then((res) => res.Body.toString('utf-8'));

const parseJSONL = R.pipe(
  R.split('\n'),
  R.reject(R.isEmpty),
  R.map(JSON.parse),
);

const loadManifest = ({ s3, bucket }) => async (hash) =>
  s3
    .getObject({ Bucket: bucket, Key: `${MANIFESTS_PREFIX}${hash}` })
    .promise()
    .then(({ Body, LastModified }) => {
      const [info, ...keys] = parseJSONL(Body.toString('utf-8'));
      return { info, keys, modified: LastModified };
    });

const getRevisionIdFromKey = (key) => key.substring(key.lastIndexOf('/') + 1);
const getRevisionKeyFromId = (name, id) => `${PACKAGES_PREFIX}${name}/${id}`;

const loadRevision = ({ s3, bucket }) => async (key) => {
  const hash = await loadRevisionHash({ s3, bucket })(key);
  const { info, keys, modified } = await loadManifest({ s3, bucket })(hash);
  return {
    id: getRevisionIdFromKey(key),
    hash,
    info,
    keys,
    modified,
  };
};

export const getRevisions = ({ s3, bucket, name }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Prefix: `${PACKAGES_PREFIX}${name}/`,
    })
    .promise()
    .then(R.pipe(
      R.prop('Contents'),
      R.map(R.pipe(R.prop('Key'), loadRevision({ s3, bucket }))),
      (ps) => Promise.all(ps),
    ))
    .then(R.sortBy((r) => -r.modified));

export const fetchTree = ({ s3, bucket, name, revision }) =>
  loadRevision({ s3, bucket })(getRevisionKeyFromId(name, revision));
