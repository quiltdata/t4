import * as R from 'ramda';
import * as React from 'react';

import { BaseError } from 'utils/error';

import Message from './Message';


export class BucketError extends BaseError {}

export class AccessDenied extends BucketError {}

export class CORSError extends BucketError {}

export const displayError = (pairs = []) => R.cond([
  [R.is(CORSError), () => (
    <Message headline="Error">
      Seems like this bucket is not configured for T4.
      <br />
      <a
        href="https://github.com/quiltdata/t4/tree/master/deployment#pre-requisites"
      >
        Learn how to configure the bucket for T4
      </a>.
    </Message>
  )],
  [R.is(AccessDenied), () => (
    <Message headline="Access Denied">
      Seems like you don`t have access to this bucket.
      <br />
      <a href="https://github.com/quiltdata/t4/tree/master/deployment#permissions">
        Learn about access control in T4
      </a>.
    </Message>
  )],
  ...pairs,
  [R.T, (e) => { throw e; }],
]);
