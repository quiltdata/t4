import * as React from 'react';
// import { Link } from 'react-router-dom';

import Layout from 'components/Layout';


/* eslint-disable react/prop-types */

export const Overview = ({ match: { params } }) => (
  <Layout bucket={params.bucket} section="overview">
    <div>
      <h1>bucket overview</h1>
      <pre>{JSON.stringify(params)}</pre>
    </div>
  </Layout>
);

export const PackageList = ({ match: { params } }) => (
  <Layout bucket={params.bucket} section="packages">
    <div>
      <h1>bucket packages</h1>
      <pre>{JSON.stringify(params)}</pre>
    </div>
  </Layout>
);

export const PackageDetail = ({ match: { params } }) => (
  <Layout bucket={params.bucket} section="packages">
    <div>
      <h1>bucket package</h1>
      <pre>{JSON.stringify(params)}</pre>
    </div>
  </Layout>
);

export const Tree = ({ match: { params } }) => (
  <Layout bucket={params.bucket} section="tree">
    <div>
      <h1>bucket tree</h1>
      <pre>{JSON.stringify(params)}</pre>
    </div>
  </Layout>
);

export const Search = ({ match: { params } }) => (
  <Layout bucket={params.bucket}>
    <div>
      <h1>bucket search</h1>
      <pre>{JSON.stringify(params)}</pre>
    </div>
  </Layout>
);
