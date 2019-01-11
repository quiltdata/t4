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
    client: new S3({
      accessKeyId: 'AKIAIOSFODNN7EXAMPLE' , //Preferably read from an env variable
      secretAccessKey: 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY' ,  //Preferably read from an env variable
      endpoint: 'http://127.0.0.1:9000' ,
      s3ForcePathStyle: true, // needed with minio?
      signatureVersion: 'v4'
}),
  })),
  provide(Ctx, 'client'));

export const inject = (prop = 's3') =>
  composeHOC('AWS.S3.inject', consume(Ctx, prop));
