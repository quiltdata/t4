import { stringify } from 'query-string';
import * as R from 'ramda';
import * as React from 'react';
import { withPropsOnChange } from 'recompose';

import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';


const Ctx = React.createContext();

const ensureExists = (routes) => new Proxy(routes, {
  get: (target, name) => {
    if (name in target) return target[name];
    throw new Error(`Route '${name}' does not exist`);
  },
});

export const mkSearch = R.pipe(
  stringify,
  R.unless(R.isEmpty, (qs) => `?${qs}`),
);

export const Provider = composeComponent('NamedRoutes.Provider',
  withPropsOnChange(['routes'], ({ routes }) => ({
    paths: ensureExists(R.pluck('path', routes)),
    urls: ensureExists(R.pluck('url', routes)),
  })),
  provide(Ctx, R.pick(['paths', 'urls'])));

const expose = (key, prop, src) =>
  prop === false
    ? {}
    : { [prop == null || prop === true ? key : prop]: src[key] };

export const inject = ({ paths, urls } = {}) =>
  composeHOC('NamedRoutes.inject', consume(Ctx, (named, props) => ({
    ...props,
    ...expose('paths', paths, named),
    ...expose('urls', urls, named),
  })));
