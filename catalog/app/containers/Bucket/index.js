import * as React from 'react';

import Layout from 'components/Layout';
import SearchResults from 'containers/SearchResults';
import * as RT from 'utils/reactTools';
import withParsedQuery from 'utils/withParsedQuery';

import Summary from './Summary';

export Tree from './Tree';


/* eslint-disable react/prop-types */

export const Overview = ({ match: { params: { bucket } } }) => (
  <Layout>
    <Summary bucket={bucket} path="" progress />
  </Layout>
);

export const PackageList = () => (
  <Layout>
    <h1>Packages are coming soon</h1>
  </Layout>
);

export const PackageDetail = () => (
  <Layout>
    <h1>Packages are coming soon</h1>
  </Layout>
);

export const Search = RT.composeComponent('Bucket.Search',
  withParsedQuery,
  ({ location: { query: { q } }, match: { params: { bucket } } }) => (
    <Layout>
      <SearchResults bucket={bucket} q={q} />
    </Layout>
  ));
