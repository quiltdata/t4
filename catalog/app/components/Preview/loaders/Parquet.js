import AsyncResult from 'utils/AsyncResult';

import { PreviewData } from '../types';
import * as utils from './utils';


export const detect = utils.extIs('.parquet');

export const load = utils.previewFetcher('parquet', (json) =>
  AsyncResult.Ok(PreviewData.Parquet({ preview: json.html })));
