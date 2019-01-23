import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link, Route, Switch, matchPath } from 'react-router-dom';
import * as RC from 'recompose';
import AppBar from '@material-ui/core/AppBar';
import Tab from '@material-ui/core/Tab';
import Tabs from '@material-ui/core/Tabs';
import { withStyles } from '@material-ui/core/styles';

import Layout from 'components/Layout';
import { ThrowNotFound } from 'containers/NotFoundPage';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';

import Overview from './Overview';
import PackageDetail from './PackageDetail';
import PackageList from './PackageList';
import PackageTree from './PackageTree';
import Search from './Search';
import Tree from './Tree';


const match = (cases) => (pathname) => {
  // eslint-disable-next-line no-restricted-syntax
  for (const [section, opts] of Object.entries(cases)) {
    if (matchPath(pathname, opts)) return section;
  }
  return false;
};

const sections = {
  overview: { path: 'bucketRoot', exact: true },
  packages: { path: 'bucketPackageList' },
  tree: { path: 'bucketTree' },
  search: { path: 'bucketSearch' },
};

const getBucketSection = (paths) =>
  match(R.map(({ path, ...opts }) =>
    ({ path: paths[path], ...opts }), sections));

const NavTab = RT.composeComponent('Bucket.Layout.Tab',
  withStyles(({ spacing: { unit } }) => ({
    root: {
      minHeight: 8 * unit,
      minWidth: 120,
    },
  })),
  RC.withProps({ component: Link }),
  Tab);

const BucketLayout = RT.composeComponent('Bucket.Layout',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    section: PT.oneOf([...Object.keys(sections), false]),
  }),
  NamedRoutes.inject(),
  withStyles(({ palette }) => ({
    appBar: {
      backgroundColor: palette.common.white,
      color: palette.getContrastText(palette.common.white),
    },
  })),
  ({ classes, bucket, section = false, children, urls }) => (
    <Layout
      pre={
        <AppBar position="static" className={classes.appBar}>
          <Tabs
            value={section}
            centered
          >
            <NavTab
              label="Overview"
              value="overview"
              to={urls.bucketRoot(bucket)}
            />
            <NavTab
              label="Packages"
              value="packages"
              to={urls.bucketPackageList(bucket)}
            />
            <NavTab
              label="Files"
              value="tree"
              to={urls.bucketTree(bucket)}
            />
            {section === 'search' && (
              <NavTab
                label="Search"
                value="search"
                to={urls.bucketSearch(bucket)}
              />
            )}
          </Tabs>
        </AppBar>
      }
    >
      {children}
    </Layout>
  ));

export default RT.composeComponent('Bucket',
  ({ location, match: { params: { bucket } } }) => (
    <NamedRoutes.Inject>
      {({ paths }) => (
        <BucketLayout
          bucket={bucket}
          section={getBucketSection(paths)(location.pathname)}
        >
          <Switch>
            <Route
              path={paths.bucketRoot}
              component={Overview}
              exact
            />
            <Route
              path={paths.bucketTree}
              component={Tree}
              exact
            />
            <Route
              path={paths.bucketSearch}
              component={Search}
              exact
            />
            <Route
              path={paths.bucketPackageList}
              component={PackageList}
              exact
            />
            <Route
              path={paths.bucketPackageDetail}
              component={PackageDetail}
              exact
            />
            <Route
              path={paths.bucketPackageTree}
              component={PackageTree}
              exact
            />
            <Route
              component={ThrowNotFound}
            />
          </Switch>
        </BucketLayout>
      )}
    </NamedRoutes.Inject>
  ));
