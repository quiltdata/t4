import { createSelector } from 'reselect';

import { get } from 'utils/immutableTools';
import { splitPath } from 'utils/s3paths';

import { REDUX_KEY, README_RE, SUMMARY_RE } from './constants';


const findFile = (files, re) =>
  (files.find(({ path }) => re.test(splitPath(path).file)) || {}).path;

export default createSelector(get(REDUX_KEY), (s) => {
  const { state, result } = s.toJS();
  return {
    state,
    result:
      state === 'READY'
        ? {
          ...result,
          readme: findFile(result.files, README_RE),
          summary: findFile(result.files, SUMMARY_RE),
        }
        : result,
  };
});
