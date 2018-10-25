import { extname } from 'path';

import memoize from 'lodash/memoize';
import * as colors from 'material-ui/styles/colors';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import {
  lifecycle,
  setPropTypes,
  setStatic,
  withHandlers,
  withProps,
  withState,
} from 'recompose';
import styled from 'styled-components';
import embed from 'vega-embed';

import Markdown from 'components/Markdown';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { S3, Signer } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import * as Resource from 'utils/Resource';
import { composeComponent } from 'utils/reactTools';
import tagged from 'utils/tagged';


const ImgContent = styled.img`
  display: block;
  margin-left: auto;
  margin-right: auto;
  max-height: 100%;
  max-width: 100%;
  min-width: 20%;
`;

const IframeContent = (props) => (
  <React.Fragment>
    <iframe
      sandbox=""
      title="Preview"
      style={{
        width: '100%',
        minHeight: '80vh',
        border: 'none',
        position: 'relative',
        zIndex: 1,
      }}
      {...props}
    />
    <Placeholder />
  </React.Fragment>
);

const VegaContent = composeComponent('Browser.VegaContent',
  withState('el', 'setEl', null),
  withHandlers({
    embed: ({ el, spec }) => () => {
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

const Container = styled.div`
  align-items: flex-start;
  display: flex;
  min-height: 84px; // for spinner
  position: relative;
`;

const signImg = memoize(({ signer, handle }) => R.evolve({
  src: (src) =>
    signer.signResource({
      ptr: Resource.parse(src),
      ctx: { type: Resource.ContextType.MDImg(), handle },
    }),
}));

const signLink = memoize(({ signer, handle }) => R.evolve({
  href: (href) =>
    signer.signResource({
      ptr: Resource.parse(href),
      ctx: { type: Resource.ContextType.MDLink(), handle },
    }),
}));

const signVegaSpec = memoize(({ signer, handle }) => R.evolve({
  data: R.map(R.evolve({
    url: (url) =>
      signer.signResource({
        ptr: Resource.parse(url),
        ctx: { type: Resource.ContextType.Vega(), handle },
      }),
  })),
}));

// TODO: handle caching (use etag)
const defaultLoad = ({ handle, signer }) =>
  signer.getSignedS3URL(handle);

const HANDLERS = [
  {
    name: 'img',
    detect: ['.jpg', '.jpeg', '.png', '.gif'],
    render: (url) => <ImgContent src={url} />,
  },
  {
    name: 'md',
    detect: '.md',
    load: async ({ handle, s3 }) => {
      const data = await s3.getObject({
        Bucket: handle.bucket,
        Key: handle.key,
      }).promise();
      return data.Body.toString('utf-8');
    },
    render: (data, { signer, handle }) => (
      <Markdown
        data={data}
        processImg={signImg({ signer, handle })}
        processLink={signLink({ signer, handle })}
      />
    ),
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
    load: async ({ handle, s3, signer }) => {
      const data = await s3.getObject({
        Bucket: handle.bucket,
        Key: handle.key,
      }).promise();
      const json = data.Body.toString('utf-8');
      // console.log('vega json', json);
      const spec = JSON.parse(json);
      // TODO: validate json format
      // console.log('vega spec', spec);
      return signVegaSpec({ signer, handle })(spec);
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

const PreviewError = tagged(['Unsupported', 'DoesNotExist', 'Unknown']);

const ErrorText = styled.p`
  color: ${colors.grey500};
  font-size: 1.5em;
  margin: 0;
`;

export default composeComponent('Browser.ContentWindow',
  setStatic('supports', (key) => !!getHandler(key)),
  setPropTypes({
    handle: PT.object.isRequired,
  }),
  S3.inject(),
  Signer.inject(),
  withState('state', 'setState', AsyncResult.Init()),
  withProps(({ handle }) => ({
    handler: getHandler(handle.key),
  })),
  withHandlers({
    load: ({ setState, handler, ...props }) => async () => {
      if (!handler) {
        setState(AsyncResult.Err(PreviewError.Unsupported()));
        return;
      }

      try {
        setState(AsyncResult.Pending());

        // console.log('load', props);
        const content = await (handler.load || defaultLoad)(props);
        // console.log('load: content', content);
        // TODO: handle errors
        setState(AsyncResult.Ok(content));
      } catch (e) {
        if (e.name === 'NoSuchKey') {
          setState(AsyncResult.Err(PreviewError.DoesNotExist()));
          return;
        }
        // TODO: handle error
        // eslint-disable-next-line no-console
        console.log('Preview error:', e);
        setState(AsyncResult.Err(PreviewError.Unknown()));
      }
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.load();
    },
  }),
  ({ state, ...props }) => (
    <Container>
      {AsyncResult.case({
        Err: (e) => (
          <ErrorText>
            {PreviewError.case({
              DoesNotExist: () => 'Object does not exist',
              _: () => 'Preview not available',
            }, e)}
          </ErrorText>
        ),
        Ok: (content, { handler, ...rest }) => handler.render(content, rest),
        _: () => <Placeholder />,
      }, state, props)}
    </Container>
  ));
