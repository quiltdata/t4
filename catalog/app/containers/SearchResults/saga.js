/* sagas for SearchResults */
import sortBy from 'lodash/sortBy';
import { call, put, takeLatest } from 'redux-saga/effects';

import { ErrorDisplay } from 'utils/error';
import { captureError } from 'utils/errorReporting';

import { getSearchError, getSearchSuccess } from './actions';
import { GET_SEARCH } from './constants';


// eslint-disable-next-line no-underscore-dangle
const getKey = (h) => h._source.key;

const getTimestamp = (x) => x.timestamp || new Date(0);

const latest = (a, b) => getTimestamp(a) > getTimestamp(b) ? a : b;

const mergeVersions = (
  {
    versions = [],
    score = 0,
    ...rest
  } = {},
  {
    _score,
    _source: {
      version_id: version,
      updated,
      key,
      size,
      text,
      type,
      user_meta, // eslint-disable-line camelcase
      comment,
    },
  },
) => {
  const timestamp = new Date(updated);
  return {
    ...latest(rest, {
      path: key,
      timestamp,
      version,
      size,
      text,
      // eslint-disable-next-line camelcase
      user_meta,
      comment,
    }),
    score: Math.max(score, _score),
    versions: sortBy(versions.concat({
      id: version,
      timestamp,
      // eslint-disable-next-line camelcase
      data: { size, text, user_meta },
      score: _score,
      type,
    }), (v) => -v.timestamp.getTime()),
  };
};

const processResults = ({ hits: { hits } }) =>
  Object.values(hits.reduce((acc, hit) => ({
    ...acc,
    [getKey(hit)]: mergeVersions(acc[getKey(hit)], hit),
  }), {}));
  // TODO: sort

export function* getSearch(es, { query }) {
  try {
    // TODO: rm debug code
    window.query = query;
    const formattedquery = {
      query: {
        query_string: {
          default_field: 'content',
          quote_analyzer: 'keyword',
          query,
        },
      },
    };
    const data = yield call([es, 'search'], {
      index: 'drive',
      type: '_doc',
      body: formattedquery,
    });
    yield put(getSearchSuccess(processResults(data)));
  } catch (e) {
    yield put(getSearchError(new ErrorDisplay(
      'Search hiccup', `getSearch: ${e.message}`
    )));
    captureError(e);
  }
}

export default function* ({ es }) {
  yield takeLatest(GET_SEARCH, getSearch, es);
}
