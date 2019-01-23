import S3 from 'aws-sdk/clients/s3';
import * as React from 'react';
import { withPropsOnChange } from 'recompose';

import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';

import * as Config from './Config';


const Ctx = React.createContext();

export const Provider = composeComponent('AWS.S3.Provider',
  Config.inject(),
  withPropsOnChange(['awsConfig'], ({ awsConfig }) => ({
    client: new S3(awsConfig),
  })),
  provide(Ctx, 'client'));

export const inject = (prop = 's3') =>
  composeHOC('AWS.S3.inject', consume(Ctx, prop));

export const Inject = Ctx.Consumer;
