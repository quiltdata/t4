import { mkSearch } from 'utils/NamedRoutes';


// eslint-disable-next-line no-useless-escape
const PACKAGE_PATTERN = '[a-z0-9-_]+\/[a-z0-9-_]+';

export default {
  home: {
    path: '/',
    url: () => '/',
  },
  signIn: {
    path: '/signin',
    url: (next) => `/signin${mkSearch({ next })}`,
  },
  signOut: {
    path: '/signout',
    url: () => '/signout',
  },
  bucketRoot: {
    path: '/b/:bucket',
    url: (bucket) => `/b/${bucket}`,
  },
  bucketSearch: {
    path: '/b/:bucket/search',
    url: (bucket, q) => `/b/${bucket}/search${mkSearch({ q })}`,
  },
  bucketTree: {
    path: '/b/:bucket/tree/:path(.*)?',
    url: (bucket, path = '', version) =>
      `/b/${bucket}/tree/${path}${mkSearch({ version })}`,
  },
  bucketPackageList: {
    path: '/b/:bucket/packages/',
    url: (bucket) => `/b/${bucket}/packages/`,
  },
  bucketPackageDetail: {
    path: `/b/:bucket/packages/:name(${PACKAGE_PATTERN})`,
    url: (bucket, name) => `/b/${bucket}/packages/${name}`,
  },
  bucketPackageTree: {
    path: `/b/:bucket/packages/:name(${PACKAGE_PATTERN})/tree/:revision/:path(.*)?`,
    url: (bucket, name, revision, path = '') =>
      `/b/${bucket}/packages/${name}/tree/${revision}/${path}`,
  },
};
