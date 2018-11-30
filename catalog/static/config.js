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
    "quilt-example": {
      icon: 'https://quiltcorp.files.wordpress.com/2017/08/q.png',
      title: 'Quilt Data',
      description: 'Turbocharging your S3 Bucket',
      // eslint-disable-next-line comma-dangle
      search_endpoint: 'https://search-quilt-example-rytakqayno3rlembetdhuflrna.us-east-1.es.amazonaws.com/'
    },
    "quilt-aics": {
      icon: 'https://3c1703fe8d.site.internapcdn.net/newman/gfx/news/hires/2017/3dwindowinto.png',
      title: 'Allen Institute for Cell Science',
      description: 'Launched with a contribution from Paul G. Allen in 2014, the Allen Institute for Cell Science will serve as a catalyzing force to integrate diverse technologies and approaches at a large scale in order to study the cell as an integrated system: something that traditional academic labs cannot do. Our inaugural project, the Allen Cell Explorer, will be a novel visual, dynamic, predictive model of the cell that will accelerate cell biology and biomedical research.',
      // eslint-disable-next-line comma-dangle
      search_endpoint: 'https://search-quilt-aics-2alivodd7we6cjhcrkxguahbkm.us-east-1.es.amazonaws.com/'
    // eslint-disable-next-line comma-dangle
    }
  // eslint-disable-next-line comma-dangle
  }
};
