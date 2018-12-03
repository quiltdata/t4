import PT from 'prop-types';
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

import * as Config from './Config';
import Overview from './Overview';
import PackageDetail from './PackageDetail';
import PackageList from './PackageList';
import PackageTree from './PackageTree';
import * as Search from './Search';
import Tree from './Tree';


const getBucketSection = (pathname, paths) => {
  if (matchPath(pathname, { path: paths.bucketRoot, exact: true })) {
    return 'overview';
  }
  if (matchPath(pathname, { path: paths.bucketPackageList })) {
    return 'packages';
  }
  if (matchPath(pathname, { path: paths.bucketTree })) {
    return 'tree';
  }
  return false;
};

const NavTab = RT.composeComponent('Bucket.Layout.Tab',
  withStyles(({ spacing: { unit } }) => ({
    root: {
      color: 'inherit !important',
      minHeight: 8 * unit,
      minWidth: 120,
      outline: 'none !important',
      textDecoration: 'none !important',
    },
  })),
  RC.withProps({ component: Link }),
  Tab);

const BucketLayout = RT.composeComponent('Bucket.Layout',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    section: PT.oneOf(['overview', 'packages', 'tree', false]),
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
          </Tabs>
        </AppBar>
      }
    >
      {children}
    </Layout>
  ));

export default RT.composeComponent('Bucket',
  NamedRoutes.inject(),
  ({ paths, location, match: { params: { bucket } } }) => (
    <Config.CurrentProvider bucket={bucket}>
      <Search.Provider>
        <BucketLayout
          bucket={bucket}
          section={getBucketSection(location.pathname, paths)}
        >
          <Switch>
            <Route path={paths.bucketRoot} component={Overview} exact />
            <Route path={paths.bucketTree} component={Tree} exact />
            <Route path={paths.bucketSearch} component={Search.Results} exact />
            <Route path={paths.bucketPackageList} component={PackageList} exact />
            <Route path={paths.bucketPackageDetail} component={PackageDetail} exact />
            <Route path={paths.bucketPackageTree} component={PackageTree} exact />
            <Route component={ThrowNotFound} />
          </Switch>
        </BucketLayout>
      </Search.Provider>
    </Config.CurrentProvider>
  ));
