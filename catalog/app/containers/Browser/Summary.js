import { Card, CardText, CardTitle } from 'material-ui/Card';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import {
  lifecycle,
  setPropTypes,
  withHandlers,
  withState,
} from 'recompose';

import { S3 } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Resource from 'utils/Resource';
import { composeComponent, extractProp } from 'utils/reactTools';
import {
  getPrefix,
  withoutPrefix,
  resolveKey,
} from 'utils/s3paths';
import tagged from 'utils/tagged';

import ContentWindow from './ContentWindow';


export const SummaryItem = composeComponent('Browser.SummaryItem',
  setPropTypes({
    title: PT.node.isRequired,
    handle: PT.object.isRequired,
  }),
  NamedRoutes.inject(),
  ({ title, handle, urls }) => (
    <Card style={{ marginTop: 16 }}>
      <CardTitle
        title={<Link to={urls.browse(handle.key)}>{title}</Link>}
        titleStyle={{ fontSize: 21 }}
      />
      <CardText>
        <ContentWindow handle={handle} />
      </CardText>
    </Card>
  ));

const SummaryError = tagged([
  'Unknown',
  'InvalidJSON',
  'InvalidFormat',
]);

const isValidSummary = R.both(Array.isArray, R.all(R.is(String)));

const loadSummary = async (s3, handle) => {
  try {
    const file = await s3.getObject({
      Bucket: handle.bucket,
      Key: handle.key,
      // TODO: figure out caching issues
      IfMatch: handle.etag,
    }).promise();
    const json = file.Body.toString('utf-8');
    const summary = JSON.parse(json);
    if (!isValidSummary(summary)) {
      return AsyncResult.Err(SummaryError.InvalidFormat(summary));
    }

    const resolvePath = (path) => ({
      bucket: handle.bucket,
      key: resolveKey(handle.key, path),
    });

    const resolved = summary
      .map(R.pipe(
        Resource.parse,
        Resource.Pointer.case({
          Web: () => null, // web urls are not supported in this context
          S3: R.identity,
          S3Rel: resolvePath,
          Path: resolvePath,
        }),
      ))
      .filter((h) => h);
    return AsyncResult.Ok(resolved);
  } catch (e) {
    return AsyncResult.Err(R.cond([
      [R.is(SyntaxError), SummaryError.InvalidJSON],
      [R.T, SummaryError.Unknown],
    ])(e));
  }
};

export default composeComponent('Browser.Summary',
  setPropTypes({
    /**
     * summarize file handle
     *
     * @type {S3Handle}
     */
    handle: PT.object.isRequired,
  }),
  S3.inject(),
  withState('state', 'setState', AsyncResult.Init()),
  withHandlers({
    loadSummary: ({ s3, handle, setState }) => async () => {
      setState(AsyncResult.Pending());
      const result = await loadSummary(s3, handle);
      AsyncResult.case({
        Err: (e) => {
          const msg = SummaryError.case({
            InvalidFormat: () => 'must be a JSON array of file links',
            InvalidJSON: R.identity,
            Unknown: R.identity,
          }, e);
          // eslint-disable-next-line no-console
          console.log('Error loading summary:', msg);
        },
        _: () => {},
      }, result);
      setState(result);
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.loadSummary();
    },
  }),
  extractProp('state', AsyncResult.case({
    _: () => null,
    Ok: (summary, { handle }) =>
      summary.map((s) => (
        <SummaryItem
          key={s.key}
          // TODO: make a reusable function to compute relative s3 paths or smth
          title={withoutPrefix(getPrefix(handle.key), s.key)}
          handle={s}
        />
      )),
  })));
