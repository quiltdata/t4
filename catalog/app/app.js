/* app.js - application entry point */
// Needed for redux-saga es6 generator support
import 'babel-polyfill';
import 'whatwg-fetch';

// TODO: remove after mui v4 release
import './installStyles';
/* eslint-disable import/first */

// Import all the third party stuff
import * as React from 'react';
import ReactDOM from 'react-dom';
// import { LOCATION_CHANGE } from 'connected-react-router/immutable';
import createHistory from 'history/createBrowserHistory';
import 'sanitize.css/sanitize.css';
//  Need to bypass CSS modules used by standard loader
//  See https://github.com/react-boilerplate/react-boilerplate/issues/238#issuecomment-222080327
import { ThemeProvider } from '@material-ui/styles';

// Import root app
import Error from 'components/Error';
import * as Intercom from 'components/Intercom';
import Layout from 'components/Layout';
import App from 'containers/App';
import Placeholder from 'containers/App/Placeholder';
import LanguageProvider from 'containers/LanguageProvider';
import * as Auth from 'containers/Auth';
import * as Notifications from 'containers/Notifications';
import routes from 'constants/routes';
import * as style from 'constants/style';
import * as AWS from 'utils/AWS';
import * as APIConnector from 'utils/APIConnector';
import * as Config from 'utils/Config';
import * as Data from 'utils/Data';
import { createBoundary } from 'utils/ErrorBoundary';
import * as NamedRoutes from 'utils/NamedRoutes';
import FormProvider from 'utils/ReduxFormProvider';
import * as Cache from 'utils/ResourceCache';
import StoreProvider from 'utils/StoreProvider';
import fontLoader from 'utils/fontLoader';
import { nest } from 'utils/reactTools';
import RouterProvider, { LOCATION_CHANGE } from 'utils/router';
import mkStorage from 'utils/storage';
// import tracking from 'utils/tracking';
// Load the favicon, the manifest.json file and the .htaccess file
/* eslint-disable import/no-unresolved, import/extensions */
import '!file-loader?name=[name].[ext]!./favicon.ico';
import '!file-loader?name=[name].[ext]!./manifest.json';
import '!file-loader?name=[name].[ext]!./quilt-og.png';
import 'file-loader?name=[name].[ext]!./.htaccess';
/* eslint-enable import/no-unresolved, import/extensions */
import configureStore from './store';
// Import i18n messages
import { translationMessages } from './i18n';
// Import CSS reset and Global Styles
import './global-styles';


// listen for Roboto fonts
fontLoader('Roboto', 'Roboto Mono').then(() => {
  // reload doc when we have all custom fonts
  document.body.classList.add('fontLoaded');
});

// TODO: capture errors
const ErrorBoundary = createBoundary(() => () => (
  <Layout bare>
    <Error
      headline="Unexpected Error"
      detail="Something went wrong"
    />
  </Layout>
));

const FinalBoundary = createBoundary(() => () => (
  <h1 style={{ textAlign: 'center' }}>
    Something went wrong
  </h1>
));

// Create redux store with history
const initialState = {};
const history = createHistory();
const store = configureStore(initialState, history);
const MOUNT_NODE = document.getElementById('app');

// TODO: make storage injectable
const storage = mkStorage({ user: 'USER', tokens: 'TOKENS' });

const intercomUserSelector = (state) => {
  const { user: u } = Auth.selectors.domain(state);
  return u && {
    user_id: u.current_user,
    name: u.current_user,
    email: u.email,
  };
};

const render = (messages) => {
  ReactDOM.render(
    nest(
      FinalBoundary,
      [ThemeProvider, { theme: style.theme }],
      [StoreProvider, { store }],
      [LanguageProvider, { messages }],
      [NamedRoutes.Provider, { routes }],
      [RouterProvider, { history }],
      ErrorBoundary,
      Data.Provider,
      Cache.Provider,
      [Config.Provider, { path: '/config.json' }],
      FormProvider,
      Notifications.Provider,
      [React.Suspense, { fallback: <Placeholder /> }],
      [APIConnector.Provider, { fetch, middleware: [Auth.apiMiddleware] }],
      [Auth.Provider, { checkOn: LOCATION_CHANGE, storage }],
      [Intercom.Provider, { userSelector: intercomUserSelector }],
      AWS.Credentials.Provider,
      AWS.Config.Provider,
      AWS.S3.Provider,
      AWS.Signer.Provider,
      Notifications.WithNotifications,
      ErrorBoundary,
      App,
    ),
    MOUNT_NODE
  );
};

// track navigation
/*
store.runSaga(tracking, {
  locationChangeAction: LOCATION_CHANGE,
  token: config.mixpanelToken,
});
*/

if (module.hot) {
  // Hot reloadable React components and translation json files
  // modules.hot.accept does not accept dynamic dependencies,
  // have to be constants at compile-time
  module.hot.accept(['./i18n', 'containers/App'], () => {
    ReactDOM.unmountComponentAtNode(MOUNT_NODE);
    render(translationMessages);
  });
}

// Chunked polyfill for browsers without Intl support
if (!window.Intl) {
  import('intl')
    .then(() => Promise.all([
      import('intl/locale-data/jsonp/en.js'),
    ]))
    .then(() => render(translationMessages));
} else {
  render(translationMessages);
}

// Delete the old service worker.
if (navigator.serviceWorker) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((registration) => { registration.unregister(); });
  });
}
