import { dirname, basename, resolve } from 'path';


export const ensureNoSlash = (p) => p.replace(/\/$/, '');

export const ensureSlash = (p) => `${ensureNoSlash(p)}/`;

export const up = (prefix) => {
  const d = dirname(prefix);
  return d === '.' ? '' : ensureSlash(d);
};

export const isDir = (path) => path === '' || path.endsWith('/');

export const getPrefix = (path) => {
  if (!path) return '';
  if (isDir(path)) return path;
  const name = dirname(path);
  return name === '.' ? '' : ensureSlash(name);
};

export const getFile = (path) => {
  if (!path) return '';
  return isDir(path) ? '' : basename(path);
};

/**
 * Split path into file and prefix parts. Examples:
 *
 * path       | prefix     | file
 * -----------+------------+------
 * ''         | ''         | ''
 * 'hey'      | ''         | 'hey'
 * 'hey/'     | 'hey/'     | ''
 * 'hey/sup'  | 'hey/'     | 'sup'
 * 'hey/sup/' | 'hey/sup/' | ''
 */
export const splitPath = (path) => ({
  prefix: getPrefix(path),
  file: getFile(path),
});

export const withoutPrefix = (prefix, path) =>
  path.startsWith(prefix) ? path.replace(prefix, '') : path;


export const isS3Url = (url) => url.startsWith('s3://');

export const parseS3Url = (url) => {
  const m = url.match(/^s3:\/\/([a-z0-9-]+)\/(.+)$/);
  if (!m) throw new Error(`could not parse s3 url '${url}'`);
  return { bucket: m[1], key: m[2] };
};

/**
 * Create an S3Handle for a URL relative to the given S3Handle.
 *
 * @param {string} url
 * @param {S3Handle} referrer
 *
 * @returns {S3Handle}
 */
export const handleFromUrl = (url, referrer) => {
  // absolute url (e.g. `s3://${bucket}/${key}`)
  if (isS3Url(url)) return parseS3Url(url);
  if (!referrer) {
    throw new Error('handleFromUrl: referrer required for local URLs');
  }
  // path-like url (e.g. `dir/file.json` or `/dir/file.json`)
  return { bucket: referrer.bucket, key: resolveKey(referrer.key, url) };
};

export const resolveKey = (from, to) => resolve(`/${from}`, to).substring(1);
