import { mkSearch } from 'utils/NamedRoutes';


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
    url: (bucket, path = '') => `/b/${bucket}/tree/${path}`,
  },
  bucketPackageList: {
    path: '/b/:bucket/packages/',
    url: (bucket) => `/b/${bucket}/packages/`,
  },
  bucketPackageDetail: {
    path: '/b/:bucket/packages/:package',
    url: (bucket, pkg) => `/b/${bucket}/packages/${pkg}`,
  },
};
