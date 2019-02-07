import hljs from 'highlight.js';
import R from 'ramda';

import * as Resource from 'utils/Resource';

import { PreviewData } from '../types';
import * as utils from './utils';


const VEGA_SCHEMA = 'https://vega.github.io/schema/vega/v4.json';

const signVegaSpec = ({ signer, handle }) => R.evolve({
  data: R.map(R.evolve({
    url: (url) =>
      signer.signResource({
        ptr: Resource.parse(url),
        ctx: { type: Resource.ContextType.Vega(), handle },
      }),
  })),
});

const fetch = utils.gatedS3Request(utils.objectGetter((r, { handle, signer }) => {
  const contents = r.Body.toString('utf-8');

  try {
    const spec = JSON.parse(contents);
    if (spec.$schema === VEGA_SCHEMA) {
      return PreviewData.Vega({ spec: signVegaSpec({ signer, handle })(spec) });
    }
  } catch (e) {
    if (!(e instanceof SyntaxError)) throw e;
  }

  const lang = 'json';
  const highlighted = hljs.highlight(lang, contents).value;
  return PreviewData.Text({ contents, lang, highlighted });
}));


export const detect = utils.extIs('.json');

export const load = (handle, callback) =>
  utils.withSigner((signer) => fetch(handle, callback, { signer }));
