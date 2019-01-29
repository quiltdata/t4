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
import * as AWS from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import StyledLink from 'utils/StyledLink';
import { composeComponent } from 'utils/reactTools';
import {
  getBasename,
  getPrefix,
  withoutPrefix,
} from 'utils/s3paths';

import * as requests from './requests';


const README_RE = /^readme\.md$/i;
const SUMMARIZE_RE = /^quilt_summarize\.json$/i;
const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif'];
const MAX_THUMBNAILS = 100;

const findFile = (re) =>
  R.find((f) => re.test(getBasename(f.logicalKey || f.key)));

const extractSummary = R.applySpec({
  readme: findFile(README_RE),
  summarize: findFile(SUMMARIZE_RE),
  images: R.filter((f) =>
    IMAGE_EXTS.some((ext) => (f.logicalKey || f.key).endsWith(ext))),
});

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
  ({ handle, name }) => (
    <NamedRoutes.Inject>
      {({ urls }) => (
        <SummaryItem
          title={
            // TODO: move link generation to the upper level to support package links
            <StyledLink to={urls.bucketFile(handle.bucket, handle.key)}>
              {name || basename(handle.logicalKey || handle.key)}
            </StyledLink>
          }
        >
          <ContentWindow handle={handle} />
        </SummaryItem>
      )}
    </NamedRoutes.Inject>
  ));

const Thumbnails = composeComponent('Bucket.Summary.Thumbnails',
  RC.setPropTypes({
    images: PT.array.isRequired,
  }),
  RC.withProps(({ images }) => ({
    showing: images.slice(0, MAX_THUMBNAILS),
  })),
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
  ({ classes, images, showing }) => (
    <SummaryItem
      title={`Images (showing ${showing.length} out of ${images.length})`}
    >
      <NamedRoutes.Inject>
        {({ urls }) => (
          <AWS.Signer.Inject>
            {(signer) => (
              <div className={classes.container}>
                {showing.map((i) => (
                  <Link
                    key={i.key}
                    // TODO: move link generation to the upper level to support package links
                    to={urls.bucketFile(i.bucket, i.key, i.version)}
                    className={classes.link}
                  >
                    <img
                      className={classes.img}
                      alt={basename(i.logicalKey || i.key)}
                      title={basename(i.logicalKey || i.key)}
                      src={signer.getSignedS3URL(i)}
                    />
                  </Link>
                ))}
                {R.times(
                  (i) => <div className={classes.filler} key={`__filler${i}`} />,
                  (5 - (showing.length % 5)) % 5
                )}
              </div>
            )}
          </AWS.Signer.Inject>
        )}
      </NamedRoutes.Inject>
    </SummaryItem>
  ));

export default composeComponent('Bucket.Summary',
  RC.setPropTypes({
    // Array of handles
    files: PT.array.isRequired,
    whenEmpty: PT.func,
  }),
  withStyles(({ spacing: { unit } }) => ({
    progress: {
      marginTop: 2 * unit,
    },
  })),
  ({ classes, files, whenEmpty = () => null }) => {
    const { readme, images, summarize } = extractSummary(files);
    return (
      <React.Fragment>
        {!readme && !summarize && !images.length && whenEmpty()}
        {readme && (
          <SummaryItemFile
            title={basename(readme.logicalKey || readme.key)}
            handle={readme}
          />
        )}
        {!!images.length && <Thumbnails images={images} />}
        {summarize && (
          <AWS.S3.Inject>
            {(s3) => (
              <Data fetch={requests.summarize} params={{ s3, handle: summarize }}>
                {AsyncResult.case({
                  Err: () => null,
                  _: () => <CircularProgress className={classes.progress} />,
                  Ok: R.map((i) => (
                    <SummaryItemFile
                      key={i.key}
                      // TODO: make a reusable function to compute relative s3 paths or smth
                      title={withoutPrefix(getPrefix(summarize.key), i.key)}
                      handle={i}
                    />
                  )),
                })}
              </Data>
            )}
          </AWS.S3.Inject>
        )}
      </React.Fragment>
    );
  });
