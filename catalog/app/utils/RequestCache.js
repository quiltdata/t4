import * as I from 'immutable';
import * as R from 'ramda';
import * as React from 'react';
import * as reduxHook from 'redux-react-hook';
import * as effects from 'redux-saga/effects';

import AsyncResult from 'utils/AsyncResult';
import { useReducer } from 'utils/ReducerInjector';
import { useSaga } from 'utils/SagaInjector';
import defer from 'utils/defer';
import * as reduxTools from 'utils/reduxTools';
import * as sagaTools from 'utils/sagaTools';
import tagged from 'utils/tagged';


const REDUX_KEY = 'app/RequestCache';

const Ctx = React.createContext();

// RequestResult<O> = AsyncResult<{
//   Init: Promise<O>
//   Pending: Promise<O>
//   Err: any
//   Ok: O
// })
// Fetch<I, O> = I -> Promise<O>
// State = Map<Fetch, Map<I, RequestResult<O>>>

const Action = tagged([
  'Init', // { fetch: fn, input: any, promise, resolver }
  'Request', // { fetch: fn, input: any }
  'Response', // { fetch: fn, input: any, result: Result }
  // TODO
  // 'Dispose', // { fetch: fn, input: any }
]);

const reducer = reduxTools.withInitialState(I.Map(), Action.reducer({
  Init: ({ fetch, input, promise }) => (s) =>
    s.setIn([fetch, I.fromJS(input)], AsyncResult.Init(promise)),
  Request: ({ fetch, input }) => (s) =>
    s.updateIn([fetch, I.fromJS(input)], AsyncResult.case({
      Init: (promise) => AsyncResult.Pending(promise),
      _: () => { throw new Error('Invalid transition'); },
    })),
  Response: ({ fetch, input, result }) => (s) =>
    s.updateIn([fetch, I.fromJS(input)], AsyncResult.case({
      Pending: () => result,
      _: () => { throw new Error('Invalid transition'); },
    })),
  __: () => R.identity,
}));

const selectEntry = (fetch, input) => (s) =>
  s.getIn([REDUX_KEY, fetch, I.fromJS(input)]);

function* handleInit({ fetch, input, resolver }) {
  yield effects.put(Action.Request({ fetch, input }));
  try {
    const res = yield effects.call(fetch, input);
    yield effects.put(Action.Response({ fetch, input, result: AsyncResult.Ok(res) }));
    resolver.resolve(res);
  } catch (e) {
    yield effects.put(Action.Response({ fetch, input, result: AsyncResult.Err(e) }));
    resolver.reject(e);
  }
}

function* saga() {
  yield sagaTools.takeEveryTagged(Action.Init, handleInit);
}

// eslint-disable-next-line react/prop-types
export const Provider = ({ children }) => {
  useSaga(saga);
  useReducer(REDUX_KEY, reducer);
  const store = React.useContext(reduxHook.StoreContext);
  const accessResult = React.useCallback((fetch, input) => {
    const getEntry = () => selectEntry(fetch, input)(store.getState());
    const entry = getEntry();
    if (entry) return entry;
    store.dispatch(Action.Init({ fetch, input, ...defer() }));
    return getEntry();
  }, [store]);

  return <Ctx.Provider value={accessResult}>{children}</Ctx.Provider>;
};

export const use = () => {
  const accessResult = React.useContext(Ctx);

  const preload = React.useMemo(
    () =>
      R.pipe(accessResult, AsyncResult.case({
        Init: R.identity,
        Pending: R.identity,
        Err: (e) => Promise.reject(e),
        Ok: (x) => Promise.resolve(x),
      })),
    [accessResult],
  );

  const get = React.useMemo(
    () =>
      R.pipe(accessResult, AsyncResult.case({
        Init: (promise) => { throw promise; },
        Pending: (promise) => { throw promise; },
        Err: (e) => { throw e; },
        Ok: R.identity,
      })),
    [accessResult],
  );

  return { get, preload };
  // TODO: claim / release in useEffect
};
