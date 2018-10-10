import SignerV4 from 'aws-sdk/lib/signers/v4';
import PT from 'prop-types';
import * as React from 'react';
import { defaultProps, withPropsOnChange, setPropTypes } from 'recompose';

import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';

import * as Config from './Config';
import * as S3 from './S3';


const DEFAULT_URL_EXPIRATION = 5 * 60; // in seconds

const Ctx = React.createContext();

const parseS3Url = (url) => {
  const withoutProto = url.replace(/^(https?:)?\/\//, '');
  const match = withoutProto.match(/s3\.amazonaws\.com\/([a-z0-9-.]+)\/(.+)/);
  return !!match && { bucket: match[1], key: match[2] };
};

export const Provider = composeComponent('AWS.Signer.Provider',
  setPropTypes({
    urlExpiration: PT.number,
  }),
  defaultProps({
    urlExpiration: DEFAULT_URL_EXPIRATION,
  }),
  Config.inject(),
  S3.inject(),
  withPropsOnChange(['awsConfig', 's3'], ({
    awsConfig: { credentials },
    s3,
    urlExpiration,
  }) => ({
    signer: {
      signRequest: (request, serviceName) => {
        if (!credentials) throw new Error('sign: no credentials');
        const signer = new SignerV4(request, serviceName);
        signer.addAuthorization(credentials, new Date());
      },
      signURLForBucket: (url, s3Bucket) => {
        const info = parseS3Url(url);
        return info && info.bucket === s3Bucket
          ? s3.getSignedUrl('getObject', {
            Bucket: s3Bucket,
            Key: info.key,
            Expires: urlExpiration,
          })
          : url;
      },
    },
  })),
  provide(Ctx, 'signer'));

export const inject = (prop = 'signer') =>
  composeHOC('AWS.Signer.inject', consume(Ctx, prop));
