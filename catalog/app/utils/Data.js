import { boundMethod } from 'autobind-decorator';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import { call, put } from 'redux-saga/effects';
import { createStructuredSelector } from 'reselect';

import AsyncResult from 'utils/AsyncResult';
import { injectReducer } from 'utils/ReducerInjector';
import { injectSaga } from 'utils/SagaInjector';
import * as RT from 'utils/reactTools';
import { takeEveryTagged } from 'utils/sagaTools';
import tagged from 'utils/tagged';


const REDUX_KEY = 'data';

const Action = tagged(['Init', 'Request', 'Response']);

function* handleRequest({ dataId, requestId, fetch, params }) {
  let result;
  try {
    const res = yield call(fetch, params);
    result = AsyncResult.Ok(res);
  } catch (e) {
    result = AsyncResult.Err(e);
  }
  yield put(Action.Response({ dataId, requestId, result }));
}

function* saga() {
  yield takeEveryTagged(Action.Request, handleRequest);
}

const init = { id: -1, result: AsyncResult.Init() };

const reducer = (state = {}, action) =>
  Action.case({
    Init: (dataId) => R.assoc(dataId, init),
    Request: ({ dataId, requestId }) => R.evolve({
      [dataId]: (s) => ({ id: requestId, result: AsyncResult.Pending(s.result) }),
    }),
    Response: ({ dataId, requestId, result }) => R.evolve({
      [dataId]: (s) => s.id === requestId ? { ...s, result } : s,
    }),
    __: () => R.identity,
  })(action)(state);

const mkSelector = (dataId) => (state) =>
  (state.get(REDUX_KEY)[dataId] || init);

export const Provider = RT.composeComponent('Data.Provider',
  injectSaga(REDUX_KEY, saga),
  injectReducer(REDUX_KEY, reducer),
  RT.RenderChildren);

const nextId = (() => {
  let lastId = 0;
  return () => {
    try {
      return lastId;
    } finally {
      lastId += 1;
    }
  };
})();

export const withData = ({
  params: getParams = R.identity,
  fetch,
  name = 'data',
  id: dataId = nextId(),
  autoFetch = true,
}) =>
  RT.composeHOC('Data.withData',
    connect(createStructuredSelector({
      data: mkSelector(dataId),
    }), undefined, undefined, { pure: false }),
    (Component) =>
      class DataFetcher extends React.Component {
        componentDidMount() {
          this.props.dispatch(Action.Init(dataId));
          if (autoFetch) this.fetch(getParams(this.props));
        }

        componentDidUpdate(prevProps) {
          if (autoFetch) {
            const newParams = getParams(this.props);
            if (!R.equals(newParams, getParams(prevProps))) this.fetch(newParams);
          }
        }

        @boundMethod
        fetch(params) {
          this.props.dispatch(Action.Request({
            dataId,
            requestId: this.props.data.id + 1,
            fetch,
            params,
          }));
        }

        render() {
          const { dispatch, data: { result }, ...rest } = this.props;
          const props = { ...rest, [name]: { result, fetch: this.fetch } };
          return <Component {...props} />;
        }
      });
