import { extname } from 'path';

import PT from 'prop-types';
import * as React from 'react';
import {
  lifecycle,
  setPropTypes,
  setStatic,
  withHandlers,
  withProps,
  withStateHandlers,
} from 'recompose';
import styled from 'styled-components';
import embed from 'vega-embed';

import Markdown from 'components/Markdown';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { S3, Signer } from 'utils/AWS';
import { composeComponent } from 'utils/reactTools';


const ImgContent = styled.img`
  display: block;
  margin-left: auto;
  margin-right: auto;
  max-height: 100%;
  max-width: 100%;
  min-width: 20%;
`;

const IframeContainer = styled.div`
  height: 100%;
  width: 100%;
`;

const IframeContent = (props) => (
  <IframeContainer>
    <iframe
      sandbox=""
      title="Preview"
      style={{
        width: '100%',
        height: '100%',
        border: 'none',
        position: 'relative',
        zIndex: 1,
      }}
      {...props}
    />
    <Placeholder />
  </IframeContainer>
);

const VegaContent = composeComponent('Browser.VegaContent',
  withStateHandlers({
    el: null,
  }, {
    setEl: () => (el) => ({ el }),
  }),
  withHandlers({
    embed: ({ el, spec }) => () => {
      embed(el, spec, { actions: false });
    },
  }),
  lifecycle({
    componentDidMount() {
      this.props.embed();
    },
  }),
  ({ setEl }) => (
    <div ref={setEl} />
  ));

const Placeholder = () => (
  <Spinner
    style={{
      fontSize: '4em',
      position: 'absolute',
      left: 20,
    }}
  />
);


const HANDLERS = [
  {
    name: 'img',
    detect: ['.jpg', '.jpeg', '.png', '.gif'],
    render: (url) => <ImgContent src={url} />,
  },
  {
    name: 'md',
    detect: '.md',
    load: async ({ bucket, path, s3 }) => {
      const data = await s3.getObject({
        Bucket: bucket,
        Key: path,
      }).promise();
      return data.Body.toString('utf-8');
    },
    render: (data, { signImg }) =>
      <Markdown data={data} processImg={signImg} />,
  },
  {
    name: 'ipynb',
    detect: '.ipynb',
    render: (url) => (
      <IframeContent
        src={`${config.aws.apiGatewayUrl}/preview?url=${encodeURIComponent(url)}`}
      />
    ),
  },
  {
    name: 'html',
    detect: '.html',
    render: (url) => <IframeContent src={url} />,
  },
  {
    name: 'vega',
    detect: '.json',
    load: async ({ bucket, path, s3, signVega }) => {
      const data = await s3.getObject({
        Bucket: bucket,
        Key: path,
      }).promise();
      const json = data.Body.toString('utf-8');
      // console.log('vega json', json);
      // TODO: validate json format
      const spec = JSON.parse(json);
      // console.log('vega spec', spec);
      return signVega(spec);
    },
    render: (spec) => <VegaContent spec={spec} />,
  },
];

const normalizeMatcher = (matcher) => {
  if (typeof matcher === 'string') return (path) => extname(path).toLowerCase() === matcher;
  if (matcher instanceof RegExp) return (path) => matcher.test(path);
  if (typeof matcher === 'function') return matcher;
  throw new Error(`invalid matcher of type ${typeof matcher}`);
};

const getHandler = (path) =>
  HANDLERS.find(({ detect }) =>
    [].concat(detect)
      .map(normalizeMatcher)
      .some((matcher) => matcher(path)));

// TODO
// eslint-disable-next-line react/prop-types
const ErrorDisplay = ({ error }) => <h1>error: {error}</h1>;

const defaultLoad = ({ bucket, path, expiration, s3 }) =>
  s3.getSignedUrl('getObject', {
    Bucket: bucket,
    Key: path,
    Expires: expiration,
  });

export default composeComponent('Browser.ContentWindow',
  setStatic('supports', (path) => !!getHandler(path)),
  setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    expiration: PT.number,
  }),
  S3.inject(),
  Signer.inject(),
  withStateHandlers({
    loading: false,
    content: null,
    error: null,
  }, {
    setLoading: () => () => ({ loading: true, content: null, error: null }),
    setContent: () => (content) => ({ loading: false, content, error: null }),
    setError: () => (error) => ({ loading: false, content: null, error }),
  }),
  withProps(({ path }) => ({
    handler: getHandler(path),
  })),
  withHandlers({
    signImg: ({ signer, bucket }) => ({ src, ...img }) => ({
      src: signer.signURLForBucket(src, bucket),
      ...img,
    }),
    signVega: ({ signer, bucket }) => ({ data, ...spec }) => ({
      data: data.map(({ url, ...rest }) => ({
        url: url && signer.signURLForBucket(url, bucket),
        ...rest,
      })),
      ...spec,
    }),
  }),
  withHandlers({
    load: ({ setLoading, setContent, setError, handler, ...props }) => async () => {
      if (!handler) {
        setError('unsupported');
        return;
      }

      setLoading();

      // console.log('props', props);
      const content = await (handler.load || defaultLoad)(props);
      // console.log('content', content);
      // TODO: handle errors
      setContent(content);
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.load();
    },
  }),
  ({ handler, loading, content, error, ...props }) => {
    if (loading) return <Placeholder />;
    if (error) return <ErrorDisplay error={error} />;
    if (content) return handler.render(content, props);
    return null;
  });
