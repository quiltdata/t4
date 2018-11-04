/* Create the store with asynchronously loaded reducers */
import { routerMiddleware } from 'connected-react-router/immutable';
import { fromJS, Iterable } from 'immutable';
import { createStore, applyMiddleware } from 'redux';
import { composeWithDevTools } from 'redux-devtools-extension';
import { combineReducers } from 'redux-immutable';

import { withInjectableReducers } from 'utils/ReducerInjector';
import { withSaga } from 'utils/SagaInjector';
import { captureError } from 'utils/errorReporting';


export default function configureStore(initialState = {}, history) {
  // routerMiddleware: Syncs the location/URL path to the state
  const middlewares = [
    routerMiddleware(history),
  ];
  // log redux state in development
  if (process.env.NODE_ENV === 'development') {
    const stateTransformer = (state) =>
      // pure JS is easier to read than Immutable objects
      Iterable.isIterable(state) ? state.toJS() : state;
    // eslint-disable-next-line global-require
    const { createLogger } = require('redux-logger');
    middlewares.push(createLogger({ stateTransformer, collapsed: true }));
  }

  const composeEnhancers = composeWithDevTools({});

  return createStore(
    (state) => state, // noop reducer, the actual ones will be injected
    fromJS(initialState),
    composeEnhancers(
      withSaga({ onError: captureError }),
      applyMiddleware(...middlewares),
      withInjectableReducers(combineReducers),
    )
  );
}
