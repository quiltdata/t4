import invariant from 'invariant';
import isEmpty from 'lodash/isEmpty';
import isFunction from 'lodash/isFunction';
import isString from 'lodash/isString';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';

import Lifecycle from 'components/Lifecycle';
import * as RT from 'utils/reactTools';
import { withInitialState } from 'utils/reduxTools';


const scope = 'app/utils/ReducerInjector';

const isValidKey = (key) => isString(key) && !isEmpty(key);

/**
 * Create a reducer injector function.
 *
 * @param {function} onSet
 *   Callback that gets called with the injected reducer map when it gets updated
 *   (a new reducer injected).
 *
 * @returns {function}
 *   A reducer injector function.
 *   Takes a key (mountpoint) and a reducer.
 */
export const createReducerInjector = (onSet) => {
  const innerScope = `${scope}/createReducerInjector`;
  invariant(isFunction(onSet),
    `${innerScope}: Expected 'onSet' to be a function`);

  let reducers = {};

  return (key, reducer) => {
    const innerScope2 = `${scope}/injectReducer`;
    invariant(isValidKey(key),
      `${innerScope2}: Expected 'key' to be a non-empty string`);
    invariant(isFunction(reducer),
      `${innerScope2}: Expected 'reducer' to be a function`);
    // Check `reducers[key] === reducer` for hot reloading
    // when a key is the same but a reducer is different
    if (key in reducers && reducers[key] === reducer) return;

    onSet(reducers = { ...reducers, [key]: reducer });
  };
};

const Ctx = React.createContext();

/**
 * Provider component for reducer injection system.
 */
export const ReducerInjector = RT.composeComponent('ReducerInjector',
  RC.setPropTypes({
    /**
     * A reducer injector function.
     */
    inject: PT.func.isRequired,
  }),
  RT.provide(Ctx, R.pick(['inject'])));

/**
 * Component that injects a given reducer into the store on mount.
 */
export const Inject = RT.composeComponent('ReducerInjector.Inject',
  RC.setPropTypes({
    /**
     * A key under which the reducer gets injected.
     */
    mount: PT.string.isRequired,
    /**
     * A reducer that gets injected.
     */
    reducer: PT.func.isRequired,
  }),
  ({ children, mount, reducer }) => (
    <Ctx.Consumer>
      {({ inject }) => (
        <Lifecycle
          key={mount}
          willMount={() => inject(mount, reducer)}
        >
          {children}
        </Lifecycle>
      )}
    </Ctx.Consumer>
  ));


/**
 * Create a HOC that creates a reducer based on props and injects it into the
 * store on mount.
 * Inject component is used under the hood.
 *
 * @param {string} mount
 *   A key under which the reducer gets injected.
 *
 * @param {function} reducerFactory
 *   A function that accepts props and creates a reducer .
 *
 * @returns {reactTools.HOC}
 */
export const injectReducerFactory = (mount, reducerFactory) =>
  RT.composeHOC(`injectReducer(${mount})`, (Component) => (props) => (
    <Inject
      mount={mount}
      reducer={reducerFactory(props)}
    >
      <Component {...props} />
    </Inject>
  ));

/**
 * Create a HOC that injects a given reducer into the store on mount.
 * Inject component is used under the hood.
 *
 * @param {string} mount
 *   A key under which the reducer gets injected.
 *
 * @param {reduxTools.Reducer} reducer
 *
 * @param {function} initial
 *   A function to populate the reducer's initial state.
 *   Gets called with the props passed to the resulting component.
 *
 * @returns {reactTools.HOC}
 */
export const injectReducer = (mount, reducer, initial) =>
  injectReducerFactory(mount,
    initial
      ? (props) => withInitialState(initial(props), reducer)
      : () => reducer);

/**
 * Create a store enhancer that attaches `injectReducer` method to the store.
 *
 * @param {function} createReducer
 *   A function that creates a reducer from the given reducer map.
 *
 * @returns {reduxTools.StoreEnhancer}
 */
export const withInjectableReducers = (createReducer) => (createStore) => (...args) => {
  const store = createStore(...args);
  const inject = createReducerInjector((injected) => {
    store.replaceReducer(createReducer(injected));
  });
  return {
    ...store,
    injectReducer: inject,
  };
};
