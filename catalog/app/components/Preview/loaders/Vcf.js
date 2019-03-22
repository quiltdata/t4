import AsyncResult from 'utils/AsyncResult';

import { PreviewData } from '../types';
import * as utils from './utils';


export const detect = utils.extIs('.vcf');

export const load = utils.previewFetcher('vcf', ({ info: { data: d } }) =>
  AsyncResult.Ok(PreviewData.Vcf({
    meta: d.meta,
    header: d.header.map((row) => row.split('\t')),
    data: d.data.map((row) => row.split('\t')),
  })));
