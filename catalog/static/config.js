// eslint-disable-next-line no-underscore-dangle
window.__CONFIG = {
  alwaysRequiresAuth: false,
  api: 'not used but needs to be set :(',
  aws: {
    region: 'us-east-1',
    s3Bucket: 't4-bucket',
    apiGatewayUrl: 'https://tdfqht5b70.execute-api.us-east-1.amazonaws.com/prod',
    // eslint-disable-next-line comma-dangle
    elasticSearchUrl: 'https://search-t4-stack-vh6cadfyzemgwbdmpfjqenq36a.us-east-1.es.amazonaws.com'
  },
  configs: {
    "alpha-quilt-storage": {
      icon: 'https://d1zvn9rasera71.cloudfront.net/q-128-square.png',
      title: 'Quilt Alpha',
      description: '',
      // eslint-disable-next-line comma-dangle
      search_endpoint: 'https://search-alpha-ness-i55uw3a7cpm3aejv22y7p4ijge.us-east-1.es.amazonaws.com/'
    },
    "quilt-example": {
      menu: true,
      icon: 'https://d1zvn9rasera71.cloudfront.net/q-128-square.png',
      title: 'Quilt Example',
      description: 'T4 transforms an S3 bucket into a visual data regsitry',
      // eslint-disable-next-line comma-dangle
      search_endpoint: 'https://search-quilt-example-rytakqayno3rlembetdhuflrna.us-east-1.es.amazonaws.com/'
    },
    "quilt-aics": {
      menu: true,
      icon: 'https://3c1703fe8d.site.internapcdn.net/newman/gfx/news/hires/2017/3dwindowinto.png',
      title: 'Allen Institute for Cell Science',
      description: 'The Allen Cell Explorer is a novel visual, dynamic, predictive model of the cell that will accelerate cell biology and biomedical research.',
      // eslint-disable-next-line comma-dangle
      search_endpoint: 'https://search-quilt-aics-2alivodd7we6cjhcrkxguahbkm.us-east-1.es.amazonaws.com/'
    // eslint-disable-next-line comma-dangle
    }
  // eslint-disable-next-line comma-dangle
  }
};
