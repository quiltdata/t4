import { basename } from 'path';

import * as R from 'ramda';

import {
  ensureNoSlash,
  getBasename,
  resolveKey,
  withoutPrefix,
  up,
} from 'utils/s3paths';
import * as Resource from 'utils/Resource';

import { ListingItem } from './Listing';
import * as errors from './errors';


const catchErrors = (pairs = []) => R.cond([
  [R.propEq('message', 'Network Failure'), () => {
    throw new errors.CORSError();
  }],
  [R.propEq('message', 'Access Denied'), () => {
    throw new errors.AccessDenied();
  }],
  ...pairs,
  [R.T, (e) => { throw e; }],
]);

export const bucketListing = ({ s3, urls, bucket, path }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Delimiter: '/',
      Prefix: path,
    })
    .promise()
    .then(R.pipe(
      R.applySpec({
        directories: R.pipe(
          R.prop('CommonPrefixes'),
          R.pluck('Prefix'),
          R.filter((d) => d !== '/' && d !== '../'),
          R.uniq,
          R.map((name) =>
            ListingItem.Dir({
              name: ensureNoSlash(withoutPrefix(path, name)),
              to: urls.bucketTree(bucket, name),
            })),
        ),
        files: R.pipe(
          R.prop('Contents'),
          // filter-out "directory-files" (files that match prefixes)
          R.filter(({ Key }) => Key !== path && !Key.endsWith('/')),
          R.map(({ Key, Size, LastModified }) =>
            ListingItem.File({
              name: basename(Key),
              to: urls.bucketTree(bucket, Key),
              size: Size,
              modified: LastModified,
            })),
        ),
      }),
      ({ files, directories }) => [
        ...(
          path !== ''
            ? [ListingItem.Dir({
              name: '..',
              to: urls.bucketTree(bucket, up(path)),
            })]
            : []
        ),
        ...directories,
        ...files,
      ],
      // filter-out files with same name as one of dirs
      R.uniqBy(ListingItem.case({ Dir: R.prop('name'), File: R.prop('name') })),
    ))
    .catch(catchErrors());

const mkHandle = (bucket) => (i) => ({
  bucket,
  key: i.Key,
  modified: i.LastModified,
  size: i.Size,
  etag: i.ETag,
});

const findFile = (re) => R.find(({ key }) => re.test(getBasename(key)));

const README_RE = /^readme\.md$/i;
const SUMMARIZE_RE = /^quilt_summarize\.json$/i;
const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif'];

export const fetchSummary = ({ s3, bucket, path }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Delimiter: '/',
      Prefix: path,
    })
    .promise()
    .then(R.pipe(
      R.prop('Contents'),
      R.map(mkHandle(bucket)),
      // filter-out "directory-files" (files that match prefixes)
      R.filter((f) => f.key !== path && !f.key.endsWith('/')),
      R.applySpec({
        readme: findFile(README_RE),
        summarize: findFile(SUMMARIZE_RE),
        images: R.filter(({ key }) =>
          IMAGE_EXTS.some((ext) => key.endsWith(ext))),
      }),
    ))
    .catch(catchErrors());

const isValidManifest = R.both(Array.isArray, R.all(R.is(String)));

export const summarize = async ({ s3, handle }) => {
  if (!handle) return null;

  try {
    const file = await s3.getObject({
      Bucket: handle.bucket,
      Key: handle.key,
      // TODO: figure out caching issues
      IfMatch: handle.etag,
    }).promise();
    const json = file.Body.toString('utf-8');
    const manifest = JSON.parse(json);
    if (!isValidManifest(manifest)) {
      throw new Error(
        'Invalid manifest: must be a JSON array of file links'
      );
    }

    const resolvePath = (path) => ({
      bucket: handle.bucket,
      key: resolveKey(handle.key, path),
    });

    return manifest
      .map(R.pipe(
        Resource.parse,
        Resource.Pointer.case({
          Web: () => null, // web urls are not supported in this context
          S3: R.identity,
          S3Rel: resolvePath,
          Path: resolvePath,
        }),
      ))
      .filter((h) => h);
  } catch (e) {
    // eslint-disable-next-line no-console
    console.log('Error loading summary:');
    // eslint-disable-next-line no-console
    console.error(e);
    return [];
  }
};

const PACKAGES_PREFIX = '.quilt/named_packages/';
const MANIFESTS_PREFIX = '.quilt/packages/';

export const listPackages = async ({ s3, bucket }) =>
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
    ))
    .catch(catchErrors());

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

export const getPackageRevisions = ({ s3, bucket, name }) =>
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
    .then(R.sortBy((r) => -r.modified))
    .catch(catchErrors());

export const fetchPackageTree = ({ s3, bucket, name, revision }) =>
  loadRevision({ s3, bucket })(getRevisionKeyFromId(name, revision))
    .catch(catchErrors());

// eslint-disable-next-line no-underscore-dangle
const getKey = (h) => h._source.key;

const getTimestamp = (x) => x.timestamp || new Date(0);

const latest = (a, b) => getTimestamp(a) > getTimestamp(b) ? a : b;

const mergeVersions = (
  {
    versions = [],
    score = 0,
    ...rest
  } = {},
  {
    _score,
    _source: {
      version_id: version,
      updated,
      key: path,
      size,
      text,
      type,
      user_meta: meta,
      comment,
    },
  },
) => {
  const timestamp = new Date(updated);
  return {
    ...latest(rest, {
      path,
      timestamp,
      version,
      size,
      text,
      meta,
      comment,
    }),
    score: Math.max(score, _score),
    versions: R.sortBy(
      (v) => -v.timestamp.getTime(),
      versions.concat({
        id: version,
        timestamp,
        data: { size, text, meta },
        score: _score,
        type,
      }),
    ),
  };
};

const formatQuery = (query) => ({
  query: {
    query_string: {
      default_field: 'content',
      quote_analyzer: 'keyword',
      query,
    },
  },
});

export const search = ({ es, query }) =>
  es.search({
    index: 'drive',
    type: '_doc',
    body: formatQuery(query),
  }).then(R.pipe(
    R.path(['hits', 'hits']),
    R.reduce((acc, hit) => ({
      ...acc,
      [getKey(hit)]: mergeVersions(acc[getKey(hit)], hit),
    }), {}),
    R.values,
  ));
  // TODO: sort
  // TODO: catch / throw errors
