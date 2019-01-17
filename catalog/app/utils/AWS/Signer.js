import SignerV4 from 'aws-sdk/lib/signers/v4';
import invariant from 'invariant';
import PT from 'prop-types';
import * as React from 'react';
import { defaultProps, withPropsOnChange, setPropTypes } from 'recompose';

import * as Resource from 'utils/Resource';
import {
  composeComponent,
  composeHOC,
  provide,
  consume,
} from 'utils/reactTools';
import { resolveKey } from 'utils/s3paths';

import * as Config from './Config';
import * as S3 from './S3';


const scope = 'app/utils/AWS/Signer';

const DEFAULT_URL_EXPIRATION = 5 * 60; // in seconds

const Ctx = React.createContext();

/*
Resource.Pointer handling / signing:

------------------+------------+-------------------+--------------------------+
context           | "web" urls | s3:// urls        | paths                    |
------------------+------------+-------------------+--------------------------+
MDImg             | as is      | parsed, signed,   | considered an s3 url     |
                  |            | relative to the   |                          |
                  |            | containing file   |                          |
------------------+------------+-------------------+--------------------------+
MDLink            | as is      | parsed, signed,   | as is (relative to the   |
                  |            | relative to the   | current web UI URL)      |
                  |            | containing file   |                          |
------------------+------------+-------------------+--------------------------+
Summary           | as is      | parsed, signed,   | considered an s3 url     |
                  |            | relative to the   |                          |
                  |            | containing file   |                          |
------------------+------------+-------------------+--------------------------+
Spec              | as is      | parsed, signed,   | considered an s3 url     |
                  |            | relative to the   |                          |
                  |            | containing file   |                          |
------------------+------------+-------------------+--------------------------+
*/

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
        invariant(credentials,
          `${scope}.Provider.signer.signRequest: missing credentials`);
        const signer = new SignerV4(request, serviceName);
        signer.addAuthorization(credentials, new Date());
      },
      signResource: ({ ctx, ptr }) => {
        const sign = ({ bucket, key, version }) =>
          s3.getSignedUrl('getObject', {
            Bucket: bucket,
            Key: key,
            VersionId: version,
            Expires: urlExpiration,
          });

        return Resource.Pointer.case({
          Web: (url) => url,
          S3: ({ bucket, key, version }) =>
            sign({ bucket: bucket || ctx.handle.bucket, key, version }),
          S3Rel: (path) => sign({
            bucket: ctx.handle.bucket,
            key: resolveKey(ctx.handle.key, path),
          }),
          Path: (path) =>
            Resource.ContextType.case({
              MDLink: () => path,
              _: () => sign({
                bucket: ctx.handle.bucket,
                key: resolveKey(ctx.handle.key, path),
              }),
            }, ctx.type),
        }, ptr);
      },
      getSignedS3URL: ({ bucket, key, version }) =>
        s3.getSignedUrl('getObject', {
          Bucket: bucket,
          Key: key,
          Expires: urlExpiration,
          VersionId: version,
        }),
    },
  })),
  provide(Ctx, 'signer'));

export const inject = (prop = 'signer') =>
  composeHOC('AWS.Signer.inject', consume(Ctx, prop));

export const Inject = Ctx.Consumer;
