/* Config - environment-specific parameters */
import * as R from 'ramda';

import conforms from 'utils/conforms';


const isNullable = (type) => R.either(R.isNil, R.is(type));

const check = R.unless(
  conforms({
    alwaysRequiresAuth: R.is(Boolean),
    sentryDSN: isNullable(String),
    apiGatewayUrl: R.is(String),
    defaultBucket: R.is(String),
    buckets: R.both(R.is(Array), R.all(conforms({
      name: R.is(String),
      title: isNullable(String),
      icon: isNullable(String),
      description: isNullable(String),
      searchEndpoint: isNullable(String),
      menu: isNullable(Boolean),
    }))),
  }),
  (config) => {
    throw new Error(`Invalid config:\n${JSON.stringify(config, null, 2)}`);
  },
);

// eslint-disable-next-line no-underscore-dangle
export default check(window.__CONFIG);
