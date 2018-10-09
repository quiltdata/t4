import SignerV4 from 'aws-sdk/lib/signers/v4';
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

export const Provider = composeComponent('AWS.Signer.Provider',
  Config.inject(),
  withPropsOnChange(['awsConfig'], ({ awsConfig: { credentials } }) => ({
    signer: {
      signRequest: (request, serviceName) => {
        // console.log('sign req', serviceName, credentials, request);
        if (!credentials) throw new Error('sign: no credentials');
        const signer = new SignerV4(request, serviceName);
        signer.addAuthorization(credentials, new Date());
        // console.log('signed req', request);
      },
      signURL: (url) => {
        console.log('sign url', url);
        return url;
      },
    },
  })),
  provide(Ctx, 'signer'));

export const inject = (prop = 'signer') =>
  composeHOC('AWS.Signer.inject', consume(Ctx, prop));
