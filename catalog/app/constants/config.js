/* Config - environment-specific parameters */

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

/* eslint-disable no-underscore-dangle */
const config = { buckets, ...window.__CONFIG };
Object.freeze(config);

const mustHave = {
  alwaysRequiresAuth: 'boolean',
  // eslint-disable-next-line comma-dangle
  api: 'string'
};

const mustHaveTeam = {
  // eslint-disable-next-line comma-dangle
  team: 'object'
};

const mustHaveInTeam = {
  // eslint-disable-next-line comma-dangle
  id: 'string'
};

const shouldHaveInTeam = {
  // eslint-disable-next-line comma-dangle
  name: 'string'
};

// TODO: use lodash/conformsTo
// test the config object
check(mustHave, window.__CONFIG);
if (window.__CONFIG.team) {
  check(mustHaveTeam, window.__CONFIG);
  check(mustHaveInTeam, window.__CONFIG.team);
  check(shouldHaveInTeam, window.__CONFIG.team, false);
}

function check(expected, actual, error = true) {
  Object.keys(expected).forEach((key) => {
    const expectedType = expected[key];
    const actualValue = actual[key];
    const actualType = typeof actualValue;
    if ((actualType !== expectedType) || (actualType === 'string' && actualValue.length < 1)) {
      const msg = `Unexpected config['${key}']: ${actualValue}`;
      if (error) {
        throw new Error(msg);
      }
      // eslint-disable-next-line no-console
      console.warn(msg, window.__CONFIG);
    }
  });
}
/* eslint-enable no-underscore-dangle */

export default config;
