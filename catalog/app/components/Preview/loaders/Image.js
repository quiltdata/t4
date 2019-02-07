import { PreviewData } from '../types';

import * as utils from './utils';


export const detect =
  utils.extIn(['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']);

const sign = async ({ handle, signer }) =>
  PreviewData.Image({ url: signer.getSignedS3URL(handle) });

export const load = utils.gatedS3Request(({ handle, gated }, callback) =>
  utils.withSigner((signer) =>
    utils.withData(
      { fetch: sign, params: { handle, signer }, noAutoFetch: gated },
      callback,
    )));
