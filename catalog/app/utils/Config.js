import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';

import { withData } from 'utils/Data';
import * as RT from 'utils/reactTools';
import { conforms, isNullable, isArrayOf } from 'utils/validate';


// TODO: rm after debugging
/* eslint-disable no-console */
const validateConfig = conforms({
  alwaysRequiresAuth: R.is(Boolean),
  sentryDSN: isNullable(String),
  apiGatewayEndpoint: R.is(String),
  defaultBucket: R.is(String),
  suggestedBuckets: isArrayOf(R.is(String)),
  federations: isArrayOf(R.is(String)),
});

const Ctx = React.createContext();

export const Provider = RT.composeComponent('Config.Provider',
  RC.setPropTypes({
    path: PT.string.isRequired,
  }),
  withData({
    params: R.pick(['path']),
    fetch: async ({ path }) => {
      try {
        const res = await fetch(path);
        if (!res.ok) {
          console.log('config res !ok', res);
          throw new Error('config request error');
        }
        const json = await res.json();
        if (!validateConfig(json)) {
          console.log('invalid config', json);
          throw new Error('invalid config');
        }
        console.log('cfg json', json);
        return json;
      } catch (e) {
        console.log('config error', e);
        throw e;
      }
    },
  }),
  // TODO: display error
  RT.provide(Ctx, R.path(['data', 'result'])));

export const Inject = Ctx.Consumer;

export const inject = (prop = 'config') =>
  RT.composeHOC('Config.inject',
    RT.consume(Ctx, prop));
