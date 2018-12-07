/* Config - environment-specific parameters */
import conforms from 'lodash/conforms';
import * as R from 'ramda';


// hardcode the buckets for now
const buckets = [
  {
    name: 'quilt-example',
    title: 'Quilt Data',
    icon: 'https://quiltcorp.files.wordpress.com/2017/08/q.png',
    description: 'Turbocharging your S3 Bucket',
    searchEndpoint: 'https://search-quilt-example-rytakqayno3rlembetdhuflrna.us-east-1.es.amazonaws.com/',
  },
  {
    name: 'quilt-aics',
    title: 'Allen Institute for Cell Science',
    icon: 'https://3c1703fe8d.site.internapcdn.net/newman/gfx/news/hires/2017/3dwindowinto.png',
    description: 'Launched with a contribution from Paul G. Allen in 2014, the Allen Institute for Cell Science will serve as a catalyzing force to integrate diverse technologies and approaches at a large scale in order to study the cell as an integrated system: something that traditional academic labs cannot do. Our inaugural project, the Allen Cell Explorer, will be a novel visual, dynamic, predictive model of the cell that will accelerate cell biology and biomedical research.',
    searchEndpoint: 'https://search-quilt-aics-2alivodd7we6cjhcrkxguahbkm.us-east-1.es.amazonaws.com/',
  },
];

const defaultBucket = 'quilt-example';

// eslint-disable-next-line no-underscore-dangle
const config = { buckets, defaultBucket, ...window.__CONFIG };

const check = conforms({
  alwaysRequiresAuth: R.is(Boolean),
  sentryDSN: R.is(String),
  apiGatewayUrl: R.is(String),
});

if (!check(config)) {
  throw new Error(`Invalid config:\n${JSON.stringify(config, null, 2)}`);
}

export default config;
