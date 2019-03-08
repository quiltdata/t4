import { mkSearch } from 'utils/NamedRoutes';


// eslint-disable-next-line no-useless-escape
const PACKAGE_PATTERN = '[a-z0-9-_]+\/[a-z0-9-_]+';

export default {
  home: {
    path: '/',
    url: () => '/',
  },

  // auth
  signIn: {
    path: '/signin',
    url: (next) => `/signin${mkSearch({ next })}`,
  },
  signOut: {
    path: '/signout',
    url: () => '/signout',
  },
  signUp: {
    path: '/signup',
    url: () => '/signup',
  },
  passReset: {
    path: '/reset_password',
    url: () => '/reset_password',
  },
  passChange: {
    path: '/reset_password/:link',
    url: (link) => `/reset_password/${link}`,
  },
  code: {
    path: '/code',
    url: () => '/code',
  },
  activationError: {
    path: '/activation_error',
    url: () => '/activation_error',
  },

  // bucket
  bucketRoot: {
    path: '/b/:bucket',
    url: (bucket) => `/b/${bucket}`,
  },
  bucketSearch: {
    path: '/b/:bucket/search',
    url: (bucket, q) => `/b/${bucket}/search${mkSearch({ q })}`,
  },
  bucketFile: {
    path: '/b/:bucket/tree/:path+',
    url: (bucket, path, version) =>
      `/b/${bucket}/tree/${path}${mkSearch({ version })}`,
  },
  bucketDir: {
    path: '/b/:bucket/tree/:path(.+/)?',
    url: (bucket, path = '') => `/b/${bucket}/tree/${path}`,
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

  // admin
  admin: {
    path: '/admin',
    url: () => '/admin',
  },
};
