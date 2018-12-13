/* app.js - application entry point */
// Needed for redux-saga es6 generator support
import 'babel-polyfill';
import 'whatwg-fetch';

// Import all the third party stuff
import MuiThemeProviderV0 from 'material-ui/styles/MuiThemeProvider';
import { MuiThemeProvider } from '@material-ui/core/styles';
import ReactDOM from 'react-dom';
// import { LOCATION_CHANGE } from 'connected-react-router/immutable';
import createHistory from 'history/createBrowserHistory';
import 'sanitize.css/sanitize.css';
//  Need to bypass CSS modules used by standard loader
//  See https://github.com/react-boilerplate/react-boilerplate/issues/238#issuecomment-222080327
import '!!style-loader!css-loader!css/bootstrap-grid.css';

// Import root app
import App from 'containers/App';
import LanguageProvider from 'containers/LanguageProvider';
import * as AWSAuth from 'containers/AWSAuth';
import * as BucketConfig from 'containers/Bucket/Config';
import * as Notifications from 'containers/Notifications';
import routes from 'constants/routes';
import * as style from 'constants/style';
import * as AWS from 'utils/AWS';
import * as Config from 'utils/Config';
import * as Data from 'utils/Data';
import * as Federations from 'utils/Federations';
import * as NamedRoutes from 'utils/NamedRoutes';
import FormProvider from 'utils/ReduxFormProvider';
import StoreProvider from 'utils/StoreProvider';
import fontLoader from 'utils/fontLoader';
import { nest } from 'utils/reactTools';
import RouterProvider from 'utils/router';
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
      [Data.Provider, { fetch }],
      [Config.Provider, { path: '/config.json' }],
      Federations.Provider,
      FormProvider,
      [LanguageProvider, { messages }],
      Notifications.Provider,
      // TODO: figure out AWS components order / race conditions
      [AWSAuth.Provider, {
        storage,
        // TODO: inject config
        // testBucket: config.defaultBucket,
        // signInRedirect: routes.bucketRoot.url(config.defaultBucket),
      }],
      [AWS.Config.Provider, {
        credentialsSelector: AWSAuth.selectors.credentials,
      }],
      AWS.S3.Provider,
      AWS.Signer.Provider,
      // [BucketConfig.BucketsProvider, { buckets: config.buckets }],
      // TODO: inject federations
      [BucketConfig.BucketsProvider, { buckets: [] }],
      [RouterProvider, { history }],
      [MuiThemeProviderV0, { muiTheme: style.themeV0 }],
      [MuiThemeProvider, { theme: style.theme }],
      Notifications.WithNotifications,
      [NamedRoutes.Provider, { routes }],
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
