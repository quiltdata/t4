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
import * as Resource from 'utils/Resource';
import { composeComponent, extractProp } from 'utils/reactTools';
import {
  getPrefix,
  withoutPrefix,
  resolveKey,
} from 'utils/s3paths';

import ContentWindow from './ContentWindow';


export const SummaryItem = composeComponent('Browser.SummaryItem',
  setPropTypes({
    title: PT.node.isRequired,
    handle: PT.object.isRequired,
  }),
  ({ title, handle }) => (
    <Card style={{ marginTop: 16 }}>
      <CardTitle
        title={<Link to={`/browse/${handle.key}`}>{title}</Link>}
        titleStyle={{ fontSize: 21 }}
      />
      <CardText>
        <ContentWindow handle={handle} />
      </CardText>
    </Card>
  ));

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
      try {
        setState(AsyncResult.Pending());
        const file = await s3.getObject({
          Bucket: handle.bucket,
          Key: handle.key,
          // TODO: figure out caching issues
          IfMatch: handle.etag,
        }).promise();
        const json = file.Body.toString('utf-8');
        // console.log('summarize json', json);
        const summary = JSON.parse(json);
        // console.log('summarize obj', summary);
        // TODO: verify summary format
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
        setState(AsyncResult.Ok(resolved));
      } catch (e) {
        // console.log('loadSummary: error', ''+e, e);
        setState(AsyncResult.Err(e));
      }
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.loadSummary();
    },
  }),
  extractProp('state', AsyncResult.case({
    // TODO
    _: () => <h1>loading</h1>,
    Ok: (summary, { handle }) =>
      summary.map((s) => (
        <SummaryItem
          key={s.key}
          // TODO: make a reusable function to compute relative s3 paths or smth
          title={withoutPrefix(getPrefix(handle.key), s.key)}
          handle={s}
        />
      )),
    // TODO: layout
    Err: (e) => <h1>error: {`${e}`}</h1>,
  })));
