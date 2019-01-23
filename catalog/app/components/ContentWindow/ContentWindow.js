import { dirname, extname, resolve } from 'path';

import cx from 'classnames';
import memoize from 'lodash/memoize';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import embed from 'vega-embed';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import Markdown from 'components/Markdown';
import { S3, Signer } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import * as BucketConfig from 'utils/BucketConfig';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Resource from 'utils/Resource';
import Result from 'utils/Result';
import { captureError } from 'utils/errorReporting';
import { composeComponent } from 'utils/reactTools';
import tagged from 'utils/tagged';


const Placeholder = composeComponent('ContentWindow.Placeholder',
  withStyles(() => ({
    root: {
      position: 'absolute',
      left: 20,
    },
  })),
  CircularProgress);

const ImgContent = composeComponent('ContentWindow.ImgContent',
  withStyles(() => ({
    root: {
      display: 'block',
      marginLeft: 'auto',
      marginRight: 'auto',
      maxHeight: '100%',
      maxWidth: '100%',
      minWidth: '20%',
    },
  })),
  ({ classes, ...props }) =>
    <img className={classes.root} alt="" {...props} />);

const TextContent = composeComponent('ContentWindow.TextContent',
  withStyles(() => ({
    root: {
      margin: 0,
      width: '100%',
    },
  })),
  ({ classes, children }) => <pre className={classes.root}>{children}</pre>);

const IframeContent = composeComponent('ContentWindow.IframeContent',
  withStyles(() => ({
    iframe: {
      border: 'none',
      minHeight: '80vh',
      position: 'relative',
      width: '100%',
      zIndex: 1,
    },
  })),
  ({ classes, ...props }) => (
    <React.Fragment>
      <iframe
        sandbox=""
        title="Preview"
        className={classes.iframe}
        {...props}
      />
      <Placeholder />
    </React.Fragment>
  ));

const VegaContent = composeComponent('ContentWindow.VegaContent',
  RC.withState('el', 'setEl', null),
  RC.withHandlers({
    embed: ({ el, spec }) => () => {
      if (el) embed(el, spec, { actions: false });
    },
  }),
  RC.lifecycle({
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

const signImg = memoize(({ signer, handle }) => R.evolve({
  src: (src) =>
    signer.signResource({
      ptr: Resource.parse(src),
      ctx: { type: Resource.ContextType.MDImg(), handle },
    }),
}));

const processLink = memoize(({ urls, signer, handle }) => R.evolve({
  href: R.pipe(
    Resource.parse,
    Resource.Pointer.case({
      Path: (p) => {
        const hasSlash = p.endsWith('/');
        const resolved = resolve(dirname(handle.key), p).slice(1);
        const withSlash = hasSlash ? `${resolved}/` : resolved;
        return urls.bucketTree(handle.bucket, withSlash);
      },
      _: (ptr) =>
        signer.signResource({
          ptr,
          ctx: { type: Resource.ContextType.MDLink(), handle },
        }),
    }),
  ),
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
const defaultLoad = ({ handle, signer }) => {
  try {
    return Result.Ok(signer.getSignedS3URL(handle));
  } catch (e) {
    return Result.Err(PreviewError.Unknown(e));
  }
};

const VEGA_SCHEMA = 'https://vega.github.io/schema/vega/v4.json';

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
      try {
        const data = await s3.getObject({
          Bucket: handle.bucket,
          Key: handle.key,
          VersionId: handle.version,
        }).promise();
        return Result.Ok(data.Body.toString('utf-8'));
      } catch (e) {
        return Result.Err(
          e.name === 'NoSuchKey'
            ? PreviewError.DoesNotExist(handle)
            : PreviewError.Unknown(e)
        );
      }
    },
    render: (data, { urls, signer, handle }) => (
      <Markdown
        data={data}
        processImg={signImg({ signer, handle })}
        processLink={processLink({ urls, signer, handle })}
      />
    ),
  },
  {
    name: 'txt',
    detect: '.txt',
    load: async ({ handle, s3 }) => {
      try {
        const data = await s3.getObject({
          Bucket: handle.bucket,
          Key: handle.key,
          VersionId: handle.version,
        }).promise();
        return Result.Ok(data.Body.toString('utf-8'));
      } catch (e) {
        return Result.Err(
          e.name === 'NoSuchKey'
            ? PreviewError.DoesNotExist(handle)
            : PreviewError.Unknown(e)
        );
      }
    },
    render: (data) => (
      <TextContent>{data}</TextContent>
    ),
  },
  {
    name: 'ipynb',
    detect: '.ipynb',
    render: (url) => (
      <Config.Inject>
        {AsyncResult.case({
          Ok: (config) => (
            <BucketConfig.WithCurrentBucketConfig>
              {AsyncResult.case({
                Ok: (bucket) => {
                  const endpoint =
                    (bucket && bucket.apiGatewayEndpoint)
                      || config.apiGatewayEndpoint;
                  const src =
                    `${endpoint}/preview?url=${encodeURIComponent(url)}`;
                  return <IframeContent src={src} />;
                },
                _: () => <Placeholder />,
              })}
            </BucketConfig.WithCurrentBucketConfig>
          ),
          _: () => <Placeholder />,
        })}
      </Config.Inject>
    ),
  },
  {
    name: 'parquet',
    detect: '.parquet',
    render: (url) => (
      <Config.Inject>
        {AsyncResult.case({
          Ok: (config) => (
            <BucketConfig.WithCurrentBucketConfig>
              {AsyncResult.case({
                Ok: (bucket) => {
                  const endpoint =
                    (bucket && bucket.apiGatewayEndpoint)
                      || config.apiGatewayEndpoint;
                  const src =
                    `${endpoint}/preview?url=${encodeURIComponent(url)}`;
                  return <IframeContent src={src} />;
                },
                _: () => <Placeholder />,
              })}
            </BucketConfig.WithCurrentBucketConfig>
          ),
          _: () => <Placeholder />,
        })}
      </Config.Inject>
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
      try {
        const data = await s3.getObject({
          Bucket: handle.bucket,
          Key: handle.key,
          VersionId: handle.version,
        }).promise();
        const json = data.Body.toString('utf-8');
        const spec = JSON.parse(json);
        if (spec.$schema !== VEGA_SCHEMA) {
          return Result.Err(PreviewError.LoadError());
        }
        const signed = signVegaSpec({ signer, handle })(spec);
        return Result.Ok(signed);
      } catch (e) {
        return Result.Err(R.cond([
          [R.propEq('name', 'NoSuchKey'), () => PreviewError.DoesNotExist(handle)],
          [R.is(SyntaxError), PreviewError.LoadError],
          [R.T, PreviewError.Unknown],
        ])(e));
      }
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

const PreviewError = tagged([
  'Unsupported',
  'DoesNotExist',
  'Unknown',
  'LoadError',
]);

export default composeComponent('ContentWindow',
  RC.setStatic('supports', (key) => !!getHandler(key)),
  RC.setStatic('getType', R.pipe(getHandler, R.prop('name'))),
  RC.setPropTypes({
    handle: PT.object.isRequired,
  }),
  S3.inject(),
  Signer.inject(),
  NamedRoutes.inject(),
  RC.withState('state', 'setState', AsyncResult.Init()),
  RC.withProps(({ handle }) => ({
    handler: getHandler(handle.key),
  })),
  // TODO: use withData
  RC.withHandlers({
    load: ({ setState, handler, ...props }) => async () => {
      if (!handler) {
        setState(AsyncResult.Err(PreviewError.Unsupported()));
        return;
      }

      try {
        setState(AsyncResult.Pending());

        const result = await (handler.load || defaultLoad)(props);

        setState(Result.case({
          Ok: AsyncResult.Ok,
          Err: (e) => {
            PreviewError.case({
              Unknown: captureError,
              _: () => {},
              __: () => {},
            }, e);
            return AsyncResult.Err(e);
          },
        }, result));
      } catch (e) {
        captureError(e);
        setState(AsyncResult.Err(PreviewError.Unknown()));
      }
    },
  }),
  RC.lifecycle({
    componentWillMount() {
      this.props.load();
    },
  }),
  withStyles(() => ({
    root: {
      alignItems: 'flex-start',
      display: 'flex',
      minHeight: 40, // for spinner
      position: 'relative',
    },
  })),
  ({ className, classes, state, ...props }) => (
    <div className={cx(className, classes.root)}>
      {AsyncResult.case({
        Err: (e) => (
          <Typography color="textSecondary">
            {PreviewError.case({
              DoesNotExist: () => 'Object does not exist',
              _: () => 'Preview not available',
            }, e)}
          </Typography>
        ),
        Ok: (content, { handler, ...rest }) => handler.render(content, rest),
        _: () => <Placeholder />,
      }, state, props)}
    </div>
  ));
