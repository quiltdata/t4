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
import {
  handleFromUrl,
} from 'utils/s3paths';


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
      // console.log('embed', el, spec);
      if (el) embed(el, spec, { actions: false });
    },
  }),
  lifecycle({
    componentDidMount() {
      this.props.embed();
    },
    componentDidUpdate(prevProps) {
      if (prevProps.el !== this.props.el) this.props.embed();
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
    load: async ({ object, s3 }) => {
      const data = await s3.getObject({
        Bucket: object.bucket,
        Key: object.key,
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
    load: async ({ object, s3, signVega }) => {
      const data = await s3.getObject({
        Bucket: object.bucket,
        Key: object.key,
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
  if (typeof matcher === 'string') return (key) => extname(key).toLowerCase() === matcher;
  if (matcher instanceof RegExp) return (key) => matcher.test(key);
  if (typeof matcher === 'function') return matcher;
  throw new Error(`invalid matcher of type ${typeof matcher}`);
};

const getHandler = (key) =>
  HANDLERS.find(({ detect }) =>
    [].concat(detect)
      .map(normalizeMatcher)
      .some((matcher) => matcher(key)));

// TODO
// eslint-disable-next-line react/prop-types
const ErrorDisplay = ({ error }) => <h1>error: {`${error}`}</h1>;

// TODO: handle caching (use etag)
const defaultLoad = ({ object, expiration, s3 }) =>
  s3.getSignedUrl('getObject', {
    Bucket: object.bucket,
    Key: object.key,
    Expires: expiration,
  });

export default composeComponent('Browser.ContentWindow',
  setStatic('supports', (key) => !!getHandler(key)),
  setPropTypes({
    object: PT.object.isRequired,
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
  withProps(({ object }) => ({
    handler: getHandler(object.key),
  })),
  withHandlers({
    signImg: ({ signer, object }) => ({ src, ...img }) => ({
      // TODO: refactor
      src: signer.signURLForBucket(src, object.bucket),
      ...img,
    }),
    signVega: ({ signer, object }) => ({ data, ...spec }) => ({
      data: data.map(({ url, ...rest }) => ({
        url: url && signer.getSignedS3Url(handleFromUrl(url, object)),
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

      try {
        setLoading();

        // console.log('load', props);
        const content = await (handler.load || defaultLoad)(props);
        // console.log('load: content', content);
        // TODO: handle errors
        setContent(content);
      } catch (e) {
        // console.log('load: error', e);
        setError(e);
      }
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
