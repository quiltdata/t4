import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Icon from '@material-ui/core/Icon';
import IconButton from '@material-ui/core/IconButton';
import Typography from '@material-ui/core/Typography';
import * as colors from '@material-ui/core/colors';
import { withStyles } from '@material-ui/core/styles';

import Error from 'components/Error';
import Tag from 'components/Tag';
import Working from 'components/Working';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import * as BucketConfig from 'utils/BucketConfig';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';
import { getBreadCrumbs } from 'utils/s3paths';
import { readableBytes } from 'utils/string';
import withParsedQuery from 'utils/withParsedQuery';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import Message from './Message';
import * as requests from './requests';


const Version = RT.composeComponent('Bucket.Search.Version',
  RC.setPropTypes({
    id: PT.string.isRequired,
    ts: PT.instanceOf(Date).isRequired,
    latest: PT.bool,
  }),
  withStyles(({ typography }) => ({
    root: {
      opacity: 0.7,
    },
    ts: {
      fontWeight: typography.fontWeightRegular,
    },
  })),
  ({ classes, id, ts, latest = false }) => (
    <li className={classes.root}>
      <code>{id || '<EMPTY>'}</code>
      <span> from </span>
      <span className={classes.ts}>{ts.toLocaleString()}</span>
      {latest && <Tag>latest</Tag>}
    </li>
  ));


const Crumbs = RT.composeComponent('Bucket.Search.Crumbs',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
  }),
  ({ bucket, path }) => (
    <NamedRoutes.Inject>
      {({ urls }) => {
        const items = R.intersperse(Crumb.Sep(' / '),
          getBreadCrumbs(path).map(({ label, path: segPath }) =>
            Crumb.Segment({
              label,
              to: urls.bucketTree(bucket, segPath),
            })));
        return <BreadCrumbs items={items} />;
      }}
    </NamedRoutes.Inject>
  ));

const HitHeading = RT.composeComponent('Bucket.Search.HitHeading',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
  }),
  withStyles(() => ({
    root: {
      alignItems: 'center',
      display: 'flex',
    },
    spacer: {
      flexGrow: 1,
    },
    buttonContainer: {
      alignItems: 'center',
      display: 'flex',
      height: 24,
      justifyContent: 'center',
      width: 24,
    },
    button: {
      textDecoration: 'none !important',
    },
  })),
  ({ classes, bucket, path }) => (
    <div className={classes.root}>
      <Crumbs bucket={bucket} path={path} />
      <div className={classes.spacer} />
      <AWS.Signer.Inject>
        {(signer) => (
          <span className={classes.buttonContainer}>
            <IconButton
              className={classes.button}
              href={signer.getSignedS3URL({ bucket, key: path })}
              title="Download"
            >
              <Icon>arrow_downward</Icon>
            </IconButton>
          </span>
        )}
      </AWS.Signer.Inject>
    </div>
  ));

const Hit = RT.composeComponent('Bucket.Search.Hit',
  RC.setPropTypes({
    path: PT.string.isRequired,
    bucket: PT.string.isRequired,
    timestamp: PT.instanceOf(Date).isRequired,
    size: PT.number.isRequired,
    text: PT.string,
    meta: PT.any,
    versions: PT.array.isRequired,
  }),
  withStyles(({ palette, spacing: { unit } }) => ({
    root: {
      marginBottom: 2 * unit,
    },
    content: {
      paddingBottom: 0, // TODO: check if necessary
    },
    sectionHeading: {
      fontSize: 18, // TODO: use typog
      fontWeight: 400, // TODO: use typog
      marginBottom: 0,
      marginTop: 3 * unit,
    },
    text: {
      background: palette.grey[50],
      borderColor: palette.grey[400],
      opacity: 0.7,
    },
    meta: {
      background: colors.lightBlue[50],
      borderColor: colors.lightBlue[400],
      opacity: 0.7,
    },
    versions: {
      listStyle: 'none',
      paddingLeft: 0,
    },
    footer: {
      color: palette.grey[500],
      marginTop: '1.5em', // TODO: use units
    },
  })),
  ({
    classes,
    path,
    bucket,
    timestamp,
    size,
    text,
    meta,
    versions,
  }) => (
    <Card className={classes.root}>
      <CardContent className={classes.content}>
        <HitHeading bucket={bucket} path={path} />
        {!!text && <pre className={classes.text}>{text}</pre>}
        {!!meta && (
          <React.Fragment>
            <h2 className={classes.sectionHeading}>Metadata</h2>
            <pre className={classes.meta}>{JSON.stringify(meta, null, 2)}</pre>
          </React.Fragment>
        )}
        {versions.length && (
          <React.Fragment>
            <h2 className={classes.sectionHeading}>Versions</h2>
            <ul className={classes.versions}>
              {versions.map(({ id, timestamp: ts }, idx) => (
                <Version
                  key={id}
                  latest={idx === 0}
                  id={id}
                  ts={ts}
                />
              ))}
            </ul>
          </React.Fragment>
        )}
        <div className={classes.footer}>
          Updated {timestamp.toLocaleString()}
          &nbsp;&nbsp;&nbsp;&nbsp;
          {readableBytes(size)}
        </div>
      </CardContent>
    </Card>
  ));

const NothingFound = () => (
  <Card>
    <CardContent>
      {/* TODO: use appropriate typography */}
      <Typography>Nothing found</Typography>
      <Typography>We have not found anything matching your query</Typography>
    </CardContent>
  </Card>
);

const Browse = RT.composeComponent('Bucket.Search.Browse',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
  }),
  ({ bucket }) => (
    <NamedRoutes.Inject>
      {({ urls }) => (
        <Button
          component={Link}
          to={urls.bucketRoot(bucket)}
          variant="outlined"
        >
          Browse the bucket
        </Button>
      )}
    </NamedRoutes.Inject>
  ));

export default RT.composeComponent('Bucket.Search',
  withParsedQuery,
  ({ location: { query: { q: query = '' } } }) => (
    <BucketConfig.WithCurrentBucketConfig>
      {AsyncResult.case({
        // eslint-disable-next-line react/prop-types
        Ok: ({ name, searchEndpoint }) => searchEndpoint
          ? (
            <AWS.ES.Provider host={searchEndpoint} log="trace">
              <AWS.ES.Inject>
                {(es) => (
                  <Data fetch={requests.search} params={{ es, query }}>
                    {AsyncResult.case({
                      Ok: (results) => (
                        <React.Fragment>
                          <h1>Search Results</h1>
                          {results.length
                            ? results.map((result) =>
                              <Hit key={result.path} bucket={name} {...result} />)
                            : <NothingFound />
                          }
                          <Browse bucket={name} />
                        </React.Fragment>
                      ),
                      Err: (error) => (
                        // TODO: use Message
                        <Error {...error} />
                      ),
                      _: () => (
                        // TODO: use consistent placeholder
                        <Working>Searching</Working>
                      ),
                    })}
                  </Data>
                )}
              </AWS.ES.Inject>
            </AWS.ES.Provider>
          )
          : (
            <Message headline="Search Not Available">
              This bucket has no configured search endpoint.
            </Message>
          ),
        // TODO: use consistent placeholder
        _: () => <Working />,
      })}
    </BucketConfig.WithCurrentBucketConfig>
  ));
