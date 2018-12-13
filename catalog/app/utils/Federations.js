import * as R from 'ramda';
import * as React from 'react';

import AsyncResult from 'utils/AsyncResult';
import * as Config from 'utils/Config';
import Data from 'utils/Data';
import * as RT from 'utils/reactTools';
import { conforms, isNullable, isArrayOf } from 'utils/validate';


// TODO: rm after debugging
/* eslint-disable no-console */
const validateBucket = conforms({
  name: R.is(String),
  title: isNullable(String),
  icon: isNullable(String),
  description: isNullable(String),
  searchEndpoint: isNullable(String),
  apiGatewayEndpoint: isNullable(String),
});

const validateFederation = conforms({
  buckets: isArrayOf(R.either(R.is(String), validateBucket)),
});

const Ctx = React.createContext();

const fetchBucket = async (b) => {
  try {
    const res = await fetch(b);
    if (!res.ok) {
      console.log('error fetching bucket config', b, res);
      throw new Error('error fetching bucket config');
    }
    const json = await res.json();
    console.log('bucket json', b, json);
    if (!validateBucket(json)) {
      throw new Error('invalid bucket config');
    }
    return json;
  } catch (e) {
    console.log('error fetching bucket config', b, e);
    return undefined;
  }
};

const fetchFederations = R.pipe(
  R.tap((fs) => {
    console.log('fetch federations', fs);
  }),
  R.map(async (f) => {
    console.log('fetching federation', f);
    try {
      const res = await fetch(f);
      if (!res.ok) {
        console.log('error fetching federation', f, res);
        throw new Error('error fetching federation');
      }
      const json = await res.json();
      console.log('federation json', f, json);
      if (!validateFederation(json)) {
        throw new Error('invalid federation format');
      }
      return await Promise.all(json.buckets.map(R.when(R.is(String), fetchBucket)));
    } catch (e) {
      console.log('error fetching federation', f, e);
      return [];
    }
  }),
  Promise.all.bind(Promise),
  R.then(R.pipe(
    R.flatten,
    R.reduce((buckets, bucket) => {
      if (!bucket) return buckets;
      console.log('reduce', buckets, bucket);
      const idx = R.findIndex(R.propEq('name', bucket.name), buckets);
      return idx === -1
        ? buckets.concat(bucket)
        : R.adjust(idx, R.mergeLeft(bucket), buckets);
    }, []),
    R.tap((result) => {
      console.log('federations fetched:', result);
    })
  )),
);


const withProvide = (render) => ({ children }) =>
  render((value) => <Ctx.Provider {...{ children, value }} />);

export const Provider = RT.composeComponent('Federations.Provider',
  withProvide((provide) => (
    <Config.Inject>
      {AsyncResult.case({
        // eslint-disable-next-line react/prop-types
        Ok: ({ federations }) => (
          <Data fetch={fetchFederations} params={federations}>
            {provide}
          </Data>
        ),
        _: provide,
      })}
    </Config.Inject>
  )));

export const Inject = Ctx.Consumer;

export const inject = (prop = 'federations') =>
  RT.composeHOC('Federations.inject',
    RT.consume(Ctx, prop));
