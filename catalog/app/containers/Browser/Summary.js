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
} from 'utils/s3paths';

import ContentWindow from './ContentWindow';


export const SummaryItem = composeComponent('Browser.SummaryItem',
  setPropTypes({
    title: PT.node.isRequired,
  }),
  ({ title, ...props }) => (
    <Card style={{ marginTop: 16 }}>
      <CardTitle title={title} />
      <CardText>
        <ContentWindow {...props} />
      </CardText>
    </Card>
  ));

export default composeComponent('Browser.Summary',
  setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    expiration: PT.number,
  }),
  S3.inject(),
  withStateHandlers({
    loading: false,
    summary: null,
  }, {
    showLoading: () => () => ({ loading: true }),
    showSummary: () => (summary) => ({ summary, loading: false }),
  }),
  withHandlers({
    loadSummary: ({ s3, bucket, path, showLoading, showSummary }) => async () => {
      showLoading();
      const json = await s3.getObject({
        Bucket: bucket,
        Key: path,
      }).promise();
      const summary = JSON.parse(json);
      // TODO: verify summary format
      showSummary(summary);
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
    bucket,
    path,
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
          title={withoutPrefix(splitPath(path).prefix, s)}
          bucket={bucket}
          path={s}
          expiration={expiration}
        />
      ));
    }
    return null;
  });
