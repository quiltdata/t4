import parse from 'csv-parse/lib/es5/sync';
import * as R from 'ramda';

import AsyncResult from 'utils/AsyncResult';

import { PreviewData } from '../types';
import * as utils from './utils';


export const detect = R.pipe(utils.stripCompression,
  utils.extIn(['.csv', '.tsv']));

export const load = utils.previewFetcher('txt', ({ info: { data } }, { handle }) => {
  const opts = {
    delimiter: utils.stripCompression(handle.key).endsWith('tsv') ? '\t' : ',',
  };
  const head = parse(data.head.join('\n'), opts);
  const tail = data.tail.length ? parse(data.tail.join('\n'), opts) : [];
  return AsyncResult.Ok(PreviewData.Table({ head, tail }));
});
