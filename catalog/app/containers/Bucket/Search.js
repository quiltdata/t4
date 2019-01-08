import * as React from 'react';

import Working from 'components/Working';
import SearchResults from 'containers/SearchResults';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import * as BucketConfig from 'utils/BucketConfig';
import SearchProvider from 'utils/SearchProvider';
import * as RT from 'utils/reactTools';
import withParsedQuery from 'utils/withParsedQuery';

import Message from './Message';


export const Provider = SearchProvider;

export const Results = RT.composeComponent('Bucket.Search.Results',
  withParsedQuery,
  ({ location: { query: { q } } }) => (
    <BucketConfig.WithCurrentBucketConfig>
      {AsyncResult.case({
        // eslint-disable-next-line react/prop-types
        Ok: ({ name, searchEndpoint }) => searchEndpoint
          ? (
            <AWS.ES.Provider host={searchEndpoint} log="trace">
              <SearchResults bucket={name} q={q} />
            </AWS.ES.Provider>
          )
          : (
            <Message headline="Search Not Available">
              This bucket has no configured search endpoint.
            </Message>
          ),
        _: () => <Working />,
      })}
    </BucketConfig.WithCurrentBucketConfig>
  ));
