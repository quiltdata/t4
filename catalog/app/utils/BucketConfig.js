import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Route } from 'react-router-dom';
import * as RC from 'recompose';

import AsyncResult from 'utils/AsyncResult';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';


export const WithBucketConfigs = RT.composeComponent(
  'BucketConfig.WithBucketConfigs',
  RC.setPropTypes({
    children: PT.func.isRequired,
    suggestedOnly: PT.bool,
  }),
  ({ children, suggestedOnly = false }) => (
    <Config.Inject>
      {AsyncResult.case({
        Ok: ({ suggestedBuckets, federations }) => {
          const filtered = suggestedOnly
            ? federations.filter(({ name }) => suggestedBuckets.includes(name))
            : federations;
          return children(AsyncResult.Ok(filtered));
        },
        _: children,
      })}
    </Config.Inject>
  ),
);

export const WithCurrentBucket = RT.composeComponent(
  'BucketConfig.WithCurrentBucket',
  RC.setPropTypes({
    children: PT.func.isRequired,
  }),
  ({ children }) => (
    <NamedRoutes.Inject>
      {({ paths }) => (
        <Route path={paths.bucketRoot}>
          {({ match }) => children(match && match.params.bucket)}
        </Route>
      )}
    </NamedRoutes.Inject>
  ),
);

export const WithCurrentBucketConfig = RT.composeComponent(
  'BucketConfig.WithCurrentBucketConfig',
  RC.setPropTypes({
    children: PT.func.isRequired,
  }),
  ({ children }) => (
    <WithCurrentBucket>
      {R.ifElse(
        Boolean,
        (bucket) => (
          <WithBucketConfigs>
            {AsyncResult.case({
              Ok: R.pipe(
                R.find(({ name }) => name === bucket),
                R.defaultTo({ name: bucket }),
                AsyncResult.Ok,
                children,
              ),
              _: children,
            })}
          </WithBucketConfigs>
        ),
        R.pipe(AsyncResult.Ok, children),
      )}
    </WithCurrentBucket>
  ),
);
