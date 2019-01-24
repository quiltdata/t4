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
import StyledLink from 'utils/StyledLink';
import { composeComponent } from 'utils/reactTools';
import {
  getPrefix,
  withoutPrefix,
} from 'utils/s3paths';

import { displayError } from './errors';
import * as requests from './requests';


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
        <StyledLink to={urls.bucketFile(handle.bucket, handle.key)}>
          {name || basename(handle.key)}
        </StyledLink>
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
            to={urls.bucketFile(i.bucket, i.key)}
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
    fetch: requests.summarize,
  }),
  ({ data: { result }, children }) => children(result));

export default composeComponent('Bucket.Summary',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    progress: PT.bool,
    whenEmpty: PT.func,
    showError: PT.bool,
  }),
  S3.inject(),
  withData({
    params: R.pick(['s3', 'bucket', 'path']),
    fetch: requests.fetchSummary,
  }),
  ({
    data: { result },
    progress = false,
    whenEmpty = () => null,
    showError = true,
  }) =>
    AsyncResult.case({
      _: () => (progress && <CircularProgress />),
      Err: showError ? displayError() : () => null,
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
    }, result));
