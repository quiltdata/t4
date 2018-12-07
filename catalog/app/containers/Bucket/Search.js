import * as React from 'react';

import SearchResults from 'containers/SearchResults';
import * as AWS from 'utils/AWS';
import SearchProvider from 'utils/SearchProvider';
import * as RT from 'utils/reactTools';
import withParsedQuery from 'utils/withParsedQuery';

import * as Config from './Config';


export const Provider = RT.composeComponent('Bucket.Search.Provider',
  RT.consume(Config.CurrentCtx, 'current'),
  ({ current, children }) => (
    current && current.searchEndpoint
      ? (
        <AWS.ES.Provider host={current.searchEndpoint} log="trace">
          <SearchProvider>
            {children}
          </SearchProvider>
        </AWS.ES.Provider>
      )
      : children
  ));

export const Results = RT.composeComponent('Bucket.Search.Results',
  withParsedQuery,
  ({ location: { query: { q } }, match: { params: { bucket } } }) => (
    <SearchResults bucket={bucket} q={q} />
  ));
