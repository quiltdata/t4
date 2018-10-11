import { Card, CardText, CardTitle } from 'material-ui/Card';
import * as React from 'react';
import PT from 'prop-types';
import {
  lifecycle,
  setPropTypes,
  withHandlers,
  withStateHandlers,
} from 'recompose';

import { S3 } from 'utils/AWS';
import { composeComponent } from 'utils/reactTools';
import {
  splitPath,
  withoutPrefix,
  handleFromUrl,
} from 'utils/s3paths';

import ContentWindow from './ContentWindow';


export const SummaryItem = composeComponent('Browser.SummaryItem',
  setPropTypes({
    title: PT.node.isRequired,
    object: PT.object.isRequired,
    expiration: PT.number,
  }),
  ({ title, object, expiration }) => (
    <Card style={{ marginTop: 16 }}>
      <CardTitle title={title} />
      <CardText>
        <ContentWindow object={object} expiration={expiration} />
      </CardText>
    </Card>
  ));

export default composeComponent('Browser.Summary',
  setPropTypes({
    // summarize json S3Handle
    object: PT.object.isRequired,
    expiration: PT.number,
  }),
  S3.inject(),
  withStateHandlers({
    loading: false,
    summary: null,
    error: null,
  }, {
    showLoading: () => () => ({ loading: true, summary: null, error: null }),
    showSummary: () => (summary) => ({ loading: false, summary, error: null }),
    showError: () => (error) => ({ loading: false, summary: null, error }),
  }),
  withHandlers({
    loadSummary: ({ s3, object, showLoading, showSummary, showError }) => async () => {
      try {
        showLoading();
        const file = await s3.getObject({
          Bucket: object.bucket,
          Key: object.key,
          // TODO: figure out caching issues
          IfMatch: object.etag,
        }).promise();
        const json = file.Body.toString('utf-8');
        // console.log('summarize json', json);
        const summary = JSON.parse(json);
        // console.log('summarize obj', summary);
        // TODO: verify summary format
        showSummary(summary);
      } catch (e) {
        // console.log('loadSummary: error', ''+e, e);
        showError(e);
      }
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.loadSummary();
    },
  }),
  ({
    loading,
    summary,
    error,
    object,
    expiration,
  }) => {
    if (loading) {
      // TODO
      return <h1>loading</h1>;
    }
    if (summary) {
      return summary.map((s) => (
        <SummaryItem
          key={s}
          // TODO: make a reusable function to compute relative s3 paths or smth
          title={withoutPrefix(splitPath(object.path).prefix, s)}
          object={handleFromUrl(s, object)}
          expiration={expiration}
        />
      ));
    }
    if (error) {
      // TODO: layout
      return <h1>error: {`${error}`}</h1>;
    }
    return null;
  });
