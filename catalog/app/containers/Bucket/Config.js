import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';

import * as RT from 'utils/reactTools';


export const BucketsCtx = React.createContext();

export const BucketsProvider = RT.composeComponent('Bucket.Config.BucketsProvider',
  RC.setPropTypes({
    buckets: PT.array.isRequired,
  }),
  RT.provide(BucketsCtx, 'buckets'));

export const CurrentCtx = React.createContext();

export const CurrentProvider = RT.composeComponent('Bucket.Config.CurrentProvider',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
  }),
  RT.consume(BucketsCtx, 'buckets'),
  RT.provide(CurrentCtx, ({ bucket, buckets }) =>
    buckets.find(R.propEq('name', bucket))));
