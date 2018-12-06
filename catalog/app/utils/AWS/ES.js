import { stringify } from 'querystring';

import AWS from 'aws-sdk/lib/core';
import es from 'elasticsearch-browser';
import omit from 'lodash/fp/omit';
import isEqual from 'lodash/isEqual';
import * as R from 'ramda';
import * as React from 'react';
import { withPropsOnChange } from 'recompose';

import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';

import * as Config from './Config';
import * as Signer from './Signer';


const Ctx = React.createContext();

const extractConfig = omit([
  'children',
]);

const shouldReinstantiate = (props, next) =>
  !isEqual(extractConfig(props), extractConfig(next));

export const Provider = composeComponent('AWS.ES.Provider',
  Config.inject(),
  Signer.inject(),
  withPropsOnChange(shouldReinstantiate, (props) => ({
    es: new es.Client({
      ...extractConfig(props),
      connectionClass: SignedConnector,
    }),
  })),
  provide(Ctx, 'es'));

export const inject = (prop = 'es') =>
  composeHOC('AWS.ES.inject', consume(Ctx, prop));

const getRegion = R.pipe(
  R.prop('hostname'),
  R.match(/\.([a-z]{2}-[a-z]+-\d)\.es\.amazonaws\.com$/),
  R.nth(1),
  R.defaultTo('us-east-1'),
);

// TODO: use injected `fetch` instead of xhr
class SignedConnector extends es.ConnectionPool.connectionClasses.xhr {
  constructor(host, config) {
    super(host, config);
    this.sign = (req) => config.signer.signRequest(req, 'es');
    this.awsConfig = config.awsConfig;
    this.endpoint = new AWS.Endpoint(host.host);
    if (host.protocol) this.endpoint.protocol = host.protocol.replace(/:?$/, ':');
    if (host.port) this.endpoint.port = host.port;
    this.httpOptions = config.httpOptions || this.awsConfig.httpOptions;
  }

  request(params, cb) {
    const request = new AWS.HttpRequest(this.endpoint, getRegion(this.endpoint));

    if (params.body) {
      request.body = params.body;
    }

    request.headers = {
      ...request.headers,
      ...params.headers,
      Host: this.endpoint.host,
    };
    delete request.headers['X-Amz-User-Agent'];
    request.method = params.method;
    request.path = params.path;
    const qs = stringify(params.query);
    if (qs) request.path += `?${qs}`;

    this.sign(request);

    delete request.headers.Host;

    const patchedParams = {
      method: request.method,
      path: request.path,
      headers: request.headers,
      body: request.body,
    };

    return super.request(patchedParams, cb);
  }
}
