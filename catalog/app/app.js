/* app.js - application entry point */
// Needed for redux-saga es6 generator support
import 'babel-polyfill';
import 'whatwg-fetch';

// Import all the third party stuff
import ReactDOM from 'react-dom';
import { LOCATION_CHANGE } from 'react-router-redux';
import createHistory from 'history/createBrowserHistory';
import 'sanitize.css/sanitize.css';
//  Need to bypass CSS modules used by standard loader
//  See https://github.com/react-boilerplate/react-boilerplate/issues/238#issuecomment-222080327
import '!!style-loader!css-loader!css/bootstrap-grid.css';

// Import root app
import App from 'containers/App';
// Import Language Provider
import LanguageProvider from 'containers/LanguageProvider';
import * as AWSAuth from 'containers/AWSAuth';
import { Provider as NotificationsProvider } from 'containers/Notifications';
import config from 'constants/config';
import { Provider as APIProvider } from 'utils/APIConnector';
import * as AWS from 'utils/AWS';
import fontLoader from 'utils/fontLoader';
import { nest } from 'utils/reactTools';
import FormProvider from 'utils/ReduxFormProvider';
import RouterProvider from 'utils/router';
import mkStorage from 'utils/storage';
import StoreProvider from 'utils/StoreProvider';
import tracking from 'utils/tracking';
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

// Create redux store with history
const initialState = {};
const history = createHistory();
const store = configureStore(initialState, history);
const MOUNT_NODE = document.getElementById('app');

const storage = mkStorage({ credentials: 'CREDENTIALS' });

const render = (messages) => {
  ReactDOM.render(
    nest(
      [StoreProvider, { store }],
      FormProvider,
      [LanguageProvider, { messages }],
      NotificationsProvider,
      [APIProvider, { fetch, base: `${config.api}/api` }],
      // TODO: figure out AWS components order / race conditions
      [AWSAuth.Provider, {
        storage,
        testBucket: config.aws.s3Bucket,
        signInRedirect: '/browse/',
      }],
      [AWS.Config.Provider, {
        credentialsSelector: AWSAuth.selectors.credentials,
        region: config.aws.region,
      }],
      AWS.S3.Provider,
      AWS.Signer.Provider,
      [AWS.ES.Provider, {
        host: config.aws.elasticSearchUrl,
        log: 'trace',
      }],
      [RouterProvider, { history }],
      App,
    ),
    MOUNT_NODE
  );
};

// track navigation
store.runSaga(tracking, {
  locationChangeAction: LOCATION_CHANGE,
  token: config.mixpanelToken,
});

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
