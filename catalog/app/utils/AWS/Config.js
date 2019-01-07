import 'aws-sdk/lib/config';
import AWS from 'aws-sdk/lib/core';
import omit from 'lodash/fp/omit';
import isEqual from 'lodash/isEqual';
import PT from 'prop-types';
import * as React from 'react';
import { connect } from 'react-redux';
import {
  setPropTypes,
  withPropsOnChange,
} from 'recompose';
import { createStructuredSelector } from 'reselect';

import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';


const Ctx = React.createContext();

const extractConfig = omit([
  'credentialsSelector',
  'dispatch',
  'children',
]);

const shouldReinstantiate = (props, next) =>
  !isEqual(extractConfig(props), extractConfig(next));

export const Provider = composeComponent('AWS.Config.Provider',
  setPropTypes({
    credentialsSelector: PT.func,
  }),
  connect(createStructuredSelector({
    credentials: (state, { credentialsSelector, credentials }) =>
      credentialsSelector ? credentialsSelector(state) : credentials,
  }), undefined, undefined, { pure: false }),
  withPropsOnChange(shouldReinstantiate, (props) => ({
    config: new AWS.Config(extractConfig(props)),
  })),
  provide(Ctx, 'config'));

export const inject = (prop = 'awsConfig') =>
  composeHOC('AWS.Config.inject', consume(Ctx, prop));
