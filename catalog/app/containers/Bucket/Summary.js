import { basename } from 'path';

import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import { S3, Signer } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Resource from 'utils/Resource';
import { composeComponent } from 'utils/reactTools';
import {
  getPrefix,
  withoutPrefix,
  resolveKey,
  getBasename,
} from 'utils/s3paths';

import Message from './Message';


const MAX_THUMBNAILS = 100;

const SummaryItem = composeComponent('Bucket.Summary.Item',
  RC.setPropTypes({
    title: PT.node.isRequired,
    children: PT.node.isRequired,
  }),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      marginTop: 2 * unit,
    },
  })),
  ({ classes, title, children }) => (
    <Card className={classes.root}>
      <CardContent>
        <Typography variant="h5">{title}</Typography>
        {children}
      </CardContent>
    </Card>
  ));

const SummaryItemFile = composeComponent('Bucket.Summary.ItemFile',
  RC.setPropTypes({
    handle: PT.object.isRequired,
    name: PT.string,
  }),
  NamedRoutes.inject(),
  ({ handle, name, urls }) => (
    <SummaryItem
      title={
        <Link to={urls.bucketTree(handle.bucket, handle.key)}>
          {name || basename(handle.key)}
        </Link>
      }
    >
      <ContentWindow handle={handle} />
    </SummaryItem>
  ));

const Thumbnails = composeComponent('Bucket.Summary.Thumbnails',
  RC.setPropTypes({
    images: PT.array.isRequired,
  }),
  Signer.inject(),
  RC.withProps(({ images }) => ({
    showing: images.slice(0, MAX_THUMBNAILS),
  })),
  NamedRoutes.inject(),
  withStyles(({ spacing: { unit } }) => ({
    container: {
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'space-between',
    },
    link: {
      flexBasis: '19%',
      marginBottom: 2 * unit,
    },
    img: {
      display: 'block',
      marginLeft: 'auto',
      marginRight: 'auto',
      maxHeight: 200,
      maxWidth: '100%',
    },
    filler: {
      flexBasis: '19%',

      '&::after': {
        content: '""',
      },
    },
  })),
  ({ classes, images, showing, signer, urls }) => (
    <SummaryItem
      title={`Images (showing ${showing.length} out of ${images.length})`}
    >
      <div className={classes.container}>
        {showing.map((i) => (
          <Link
            key={i.key}
            to={urls.bucketTree(i.bucket, i.key)}
            className={classes.link}
          >
            <img
              className={classes.img}
              alt={basename(i.key)}
              title={basename(i.key)}
              src={signer.getSignedS3URL(i)}
            />
          </Link>
        ))}
        {R.times(
          (i) => <div className={classes.filler} key={`__filler${i}`} />,
          (5 - (showing.length % 5)) % 5
        )}
      </div>
    </SummaryItem>
  ));

const mkHandle = (bucket) => (i) => ({
  bucket,
  key: i.Key,
  modified: i.LastModified,
  size: i.Size,
  etag: i.ETag,
});

const findFile = (re) => R.find(({ key }) => re.test(getBasename(key)));

const README_RE = /^readme\.md$/i;
const SUMMARIZE_RE = /^quilt_summarize\.json$/i;
const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif'];

const fetchSummary = ({ s3, bucket, path }) =>
  s3
    .listObjectsV2({
      Bucket: bucket,
      Delimiter: '/',
      Prefix: path,
    })
    .promise()
    .then(R.pipe(
      R.prop('Contents'),
      R.map(mkHandle(bucket)),
      // filter-out "directory-files" (files that match prefixes)
      R.filter((f) => f.key !== path && !f.key.endsWith('/')),
      R.applySpec({
        readme: findFile(README_RE),
        summarize: findFile(SUMMARIZE_RE),
        images: R.filter(({ key }) =>
          IMAGE_EXTS.some((ext) => key.endsWith(ext))),
      }),
    ));

const isValidManifest = R.both(Array.isArray, R.all(R.is(String)));

const fetchSummarize = async ({ s3, handle }) => {
  try {
    const file = await s3.getObject({
      Bucket: handle.bucket,
      Key: handle.key,
      // TODO: figure out caching issues
      IfMatch: handle.etag,
    }).promise();
    const json = file.Body.toString('utf-8');
    const manifest = JSON.parse(json);
    if (!isValidManifest(manifest)) {
      throw new Error(
        'Invalid manifest: must be a JSON array of file links'
      );
    }

    const resolvePath = (path) => ({
      bucket: handle.bucket,
      key: resolveKey(handle.key, path),
    });

    return manifest
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
  } catch (e) {
    // eslint-disable-next-line no-console
    console.log('Error loading summary:');
    // eslint-disable-next-line no-console
    console.error(e);
    return [];
  }
};

const Summarize = composeComponent('Bucket.Summary.Summarize',
  RC.setPropTypes({
    /**
     * summarize file handle
     *
     * @type {S3Handle}
     */
    handle: PT.object.isRequired,
  }),
  S3.inject(),
  withData({
    params: R.pick(['s3', 'handle']),
    fetch: fetchSummarize,
  }),
  ({ data: { result }, children }) => children(result));

export default composeComponent('Bucket.Summary',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    progress: PT.bool,
    whenEmpty: PT.func,
  }),
  S3.inject(),
  withData({
    params: R.pick(['s3', 'bucket', 'path']),
    fetch: fetchSummary,
  }),
  ({ data: { result }, progress = false, whenEmpty = () => null }) => (
    <React.Fragment>
      {AsyncResult.case({
        _: () => (progress && <CircularProgress />),
        Err: R.cond([
          [R.propEq('message', 'Network Failure'),
            () => (
              <Message headline="Error">
                Seems like this bucket is not configured for T4.
                <br />
                <a href="https://github.com/quiltdata/t4/tree/master/deployment#pre-requisites">Learn how to configure the bucket for T4</a>.
              </Message>
            )],
          [R.propEq('message', 'Access Denied'),
            () => (
              <Message headline="Access Denied">
                Seems like you don`t have access to this bucket.
                <br />
                <a href="TODO">Learn about access control in T4</a>.
              </Message>
            )],
          [R.T,
            () => (
              <Message headline="Error">
                Something went wrong and we are not sure why.
                <br />
                Contact <a href="TODO">our support</a> for help.
              </Message>
            )],
        ]),
        // eslint-disable-next-line react/prop-types
        Ok: ({ readme, images, summarize }) => (
          <React.Fragment>
            {!readme && !summarize && !images.length && whenEmpty()}
            {readme && (
              <SummaryItemFile
                title={basename(readme.key)}
                handle={readme}
              />
            )}
            {!!images.length && <Thumbnails images={images} />}
            {summarize && (
              <Summarize handle={summarize}>
                {AsyncResult.case({
                  Err: () => null,
                  _: () => (progress && <CircularProgress />),
                  Ok: R.map((i) => (
                    <SummaryItemFile
                      key={i.key}
                      // TODO: make a reusable function to compute relative s3 paths or smth
                      title={withoutPrefix(getPrefix(summarize.key), i.key)}
                      handle={i}
                    />
                  )),
                })}
              </Summarize>
            )}
          </React.Fragment>
        ),
      })(result)}
    </React.Fragment>
  ));
