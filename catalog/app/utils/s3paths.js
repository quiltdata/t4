import { dirname, basename } from 'path';


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
