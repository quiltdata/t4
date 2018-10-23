import * as R from 'ramda';
import { createSelector } from 'reselect';

import AsyncResult from 'utils/AsyncResult';
import { get } from 'utils/immutableTools';
import { getBasename } from 'utils/s3paths';

import { REDUX_KEY, README_RE, SUMMARY_RE } from './constants';


const findFile = (files, re) =>
  files.find(({ key }) => re.test(getBasename(key)));

export default createSelector(get(REDUX_KEY), R.pipe(
  AsyncResult.case({
    Ok: (result) => AsyncResult.Ok({
      ...result,
      readme: findFile(result.files, README_RE),
      summary: findFile(result.files, SUMMARY_RE),
    }),
    _: R.identity,
  }),
  R.objOf('state'),
));
