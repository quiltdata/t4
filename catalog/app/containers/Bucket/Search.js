import cx from 'classnames';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import Chip from '@material-ui/core/Chip';
import Icon from '@material-ui/core/Icon';
import IconButton from '@material-ui/core/IconButton';
import Typography from '@material-ui/core/Typography';
import * as colors from '@material-ui/core/colors';
import { withStyles } from '@material-ui/core/styles';

import ContentWindow from 'components/ContentWindow';
import Working from 'components/Working';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import * as BucketConfig from 'utils/BucketConfig';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import StyledLink, { linkStyle } from 'utils/StyledLink';
import * as RT from 'utils/reactTools';
import { getBreadCrumbs } from 'utils/s3paths';
import { readableBytes } from 'utils/string';
import withParsedQuery from 'utils/withParsedQuery';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import Message from './Message';
import * as requests from './requests';


const versionShape = PT.shape({
  id: PT.string.isRequired,
  updated: PT.instanceOf(Date).isRequired,
  size: PT.number.isRequired,
  type: PT.string.isRequired,
  meta: PT.any,
});

const handleShape = PT.shape({
  bucket: PT.string.isRequired,
  key: PT.string.isRequired,
  version: PT.string.isRequired,
});

const Crumbs = RT.composeComponent('Bucket.Search.Crumbs',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    version: PT.string.isRequired,
  }),
  ({ bucket, path, version }) => (
    <NamedRoutes.Inject>
      {({ urls }) => {
        const items = R.intersperse(Crumb.Sep(' / '),
          getBreadCrumbs(path).map(({ label, path: segPath }) =>
            Crumb.Segment({
              label,
              // eslint-disable-next-line no-nested-ternary
              to: segPath === path
                ? (version ? urls.bucketTree(bucket, segPath, version) : undefined)
                : urls.bucketTree(bucket, segPath),
            })));
        return <BreadCrumbs items={items} />;
      }}
    </NamedRoutes.Inject>
  ));

const Header = RT.composeComponent('Bucket.Search.Header',
  RC.setPropTypes({
    handle: handleShape.isRequired,
  }),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      display: 'flex',
      marginBottom: unit,
    },
    spacer: {
      flexGrow: 1,
    },
    buttonContainer: {
      alignItems: 'center',
      display: 'flex',
      height: 32,
      justifyContent: 'center',
      width: 24,
    },
    button: {
    },
  })),
  ({ classes, handle: h }) => (
    <div className={classes.root}>
      <Crumbs bucket={h.bucket} path={h.key} version={h.version} />
      <div className={classes.spacer} />
      {h.version
        ? (
          <AWS.Signer.Inject>
            {(signer) => (
              <span className={classes.buttonContainer}>
                <IconButton
                  className={classes.button}
                  href={signer.getSignedS3URL(h)}
                  title="Download"
                >
                  <Icon>arrow_downward</Icon>
                </IconButton>
              </span>
            )}
          </AWS.Signer.Inject>
        )
        : (
          <Chip label="DELETED" />
        )
      }
    </div>
  ));

const Section = RT.composeComponent('Bucket.Search.Section',
  withStyles(({ spacing: { unit } }) => ({
    root: {
      marginTop: 2 * unit,
    },
  })),
  ({ classes, children }) => (
    <div className={classes.root}>{children}</div>
  ));

const SectionHeading = RT.composeComponent('Bucket.Search.SectionHeading',
  ({ children, ...props }) => (
    <Typography variant="h6" {...props}>{children}</Typography>
  ));

const VersionInfo = RT.composeComponent('Bucket.Search.VersionInfo',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    version: versionShape.isRequired,
    versions: PT.arrayOf(versionShape.isRequired).isRequired,
  }),
  RC.withStateHandlers({
    versionsShown: false,
  }, {
    toggleVersions: ({ versionsShown }) => () =>
      ({ versionsShown: !versionsShown }),
  }),
  NamedRoutes.inject(),
  withStyles(({ palette, typography }) => ({
    versionContainer: {
      color: palette.text.secondary,
      fontWeight: typography.fontWeightLight,
    },
    version: {
      fontFamily: typography.monospace.fontFamily,
      fontWeight: typography.fontWeightMedium,
    },
    bold: {
      color: palette.text.primary,
      fontWeight: typography.fontWeightRegular,
    },
    seeOther: {
      borderBottom: '1px dashed',
      cursor: 'pointer',
      ...linkStyle,
    },
  })),
  ({
    classes,
    bucket,
    path,
    version,
    versions,
    toggleVersions,
    versionsShown,
    urls,
  }) => (
    <React.Fragment>
      <Typography variant="subtitle1" className={classes.versionContainer}>
        {version.id
          ? (
            <span>
              {'Version '}
              <StyledLink
                to={urls.bucketTree(bucket, path, version.id)}
                className={classes.version}
              >
                {version.id}
              </StyledLink>
              {' from '}
              <span className={classes.bold}>{version.updated.toLocaleString()}</span>
              {' | '}
              <span className={classes.bold}>{readableBytes(version.size)}</span>
            </span>
          )
          : (
            <span>
              <span className={classes.bold}>Deleted</span>
              {' on '}
              <span className={classes.bold}>{version.updated.toLocaleString()}</span>
            </span>
          )
        }
        {versions.length > 1 && (
          <React.Fragment>
            {' '}
            {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions, jsx-a11y/click-events-have-key-events */}
            <span className={classes.seeOther} onClick={toggleVersions}>
              {versionsShown ? 'hide ' : 'show '}
              all versions ({versions.length})
            </span>
          </React.Fragment>
        )}
      </Typography>
      {versions.length > 1 && versionsShown && (
        <Section>
          <SectionHeading gutterBottom>Versions ordered by relevance</SectionHeading>
          {versions.map((v) => (
            <Typography
              key={`${v.updated.getTime()}:${v.id}`}
              variant="body2"
              className={classes.versionContainer}
            >
              {v.id
                ? (
                  <span>
                    <StyledLink
                      to={urls.bucketTree(bucket, path, v.id)}
                      className={classes.version}
                    >
                      {v.id}
                    </StyledLink>
                    {' from '}
                    <span className={classes.bold}>{v.updated.toLocaleString()}</span>
                    {' | '}
                    <span className={classes.bold}>{readableBytes(v.size)}</span>
                  </span>
                )
                : (
                  <span>
                    <span className={classes.bold}>Deleted</span>
                    {' on '}
                    <span className={classes.bold}>{v.updated.toLocaleString()}</span>
                  </span>
                )
              }
            </Typography>
          ))}
        </Section>
      )}
    </React.Fragment>
  ));

const Preview = RT.composeComponent('Bucket.Search.Preview',
  RC.setPropTypes({
    handle: handleShape.isRequired,
  }),
  RC.withStateHandlers(({ handle: { key } }) => ({
    loaded: ContentWindow.getType(key) !== 'ipynb',
    expanded: false,
  }), {
    load: () => () => ({ loaded: true, expanded: true }),
    expand: () => () => ({ expanded: true }),
  }),
  withStyles(({ spacing: { unit }, shape: { borderRadius }, palette }) => ({
    preview: {
      border: `1px solid ${palette.grey[300]}`,
      borderRadius,
      maxHeight: unit * 30,
      marginTop: unit,
      minHeight: unit * 15,
      overflow: 'hidden',
      padding: unit,
      position: 'relative',
    },
    previewExpanded: {
      maxHeight: 'none',
    },
    fade: {
      alignItems: 'flex-end',
      background: 'linear-gradient(to top, rgba(255,255,255,1), rgba(255,255,255,0.9), rgba(255,255,255,0))',
      bottom: 0,
      display: 'flex',
      height: unit * 10,
      justifyContent: 'center',
      left: 0,
      padding: unit,
      position: 'absolute',
      width: '100%',
    },
  })),
  // eslint-disable-next-line object-curly-newline
  ({ classes, handle, loaded, expanded, load, expand }) => {
    if (!handle.version || !ContentWindow.supports(handle.key)) return null;
    return loaded
      ? (
        <Section>
          <SectionHeading>Preview</SectionHeading>
          <div
            className={cx(classes.preview, {
              [classes.previewExpanded]: expanded,
            })}
          >
            <ContentWindow handle={handle} />
            {!expanded && (
              <div className={classes.fade}>
                <Button variant="outlined" onClick={expand}>Expand</Button>
              </div>
            )}
          </div>
        </Section>
      )
      : (
        <Section>
          <Button variant="outlined" onClick={load}>
            Load preview
          </Button>
        </Section>
      );
  });

const Meta = RT.composeComponent('Bucket.Search.Meta',
  withStyles(({ spacing: { unit } }) => ({
    meta: {
      background: colors.lightBlue[50],
      borderColor: colors.lightBlue[400],
      marginBottom: 0,
      marginTop: unit,
      opacity: 0.7,
    },
  })),
  ({ classes, meta }) =>
    !meta || R.isEmpty(meta) ? null : (
      <Section>
        <SectionHeading>Metadata</SectionHeading>
        <pre className={classes.meta}>{JSON.stringify(meta, null, 2)}</pre>
      </Section>
    ));

const getDefaultVersion = (versions) =>
  versions.find((v) => !!v.id) || versions[0];

const Hit = RT.composeComponent('Bucket.Search.Hit',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    hit: PT.shape({
      path: PT.string.isRequired,
      versions: PT.arrayOf(versionShape.isRequired).isRequired,
    }).isRequired,
  }),
  RC.withProps(({ hit: { versions } }) => ({
    version: getDefaultVersion(versions),
  })),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      marginBottom: 2 * unit,
    },
  })),
  ({ classes, bucket, hit: { path, versions }, version: v }) => (
    <Card className={classes.root}>
      <CardContent>
        <Header handle={{ bucket, key: path, version: v.id }} />
        <VersionInfo bucket={bucket} path={path} version={v} versions={versions} />
        <Meta meta={v.meta} />
        <Preview handle={{ bucket, key: path, version: v.id }} />
      </CardContent>
    </Card>
  ));

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
  withStyles(({ spacing: { unit } }) => ({
    heading: {
      marginBottom: 2 * unit,
      marginTop: 2 * unit,
    },
  })),
  withParsedQuery,
  ({ classes, location: { query: { q: query = '' } } }) => (
    <BucketConfig.WithCurrentBucketConfig>
      {AsyncResult.case({
        // eslint-disable-next-line react/prop-types
        Ok: ({ name, searchEndpoint }) => searchEndpoint
          ? (
            <AWS.ES.Provider host={searchEndpoint}>
              <AWS.ES.Inject>
                {(es) => (
                  <Data fetch={requests.search} params={{ es, query }}>
                    {AsyncResult.case({
                      // eslint-disable-next-line react/prop-types
                      Ok: ({ total, hits }) => (
                        <React.Fragment>
                          <Typography variant="h5" className={classes.heading}>
                            Search results for &quot;{query}&quot;:
                            {total
                              ? ` ${total} hits in ${hits.length} objects`
                              : ' nothing found'
                            }
                          </Typography>
                          {total
                            ? hits.map((hit) => (
                              <Hit
                                key={hit.path}
                                bucket={name}
                                hit={hit}
                              />
                            ))
                            : (
                              <React.Fragment>
                                <Typography variant="body1">
                                  We have not found anything matching your query
                                </Typography>
                                <br />
                                <Browse bucket={name} />
                              </React.Fragment>
                            )
                          }
                        </React.Fragment>
                      ),
                      Err: (error, { fetch }) => (
                        <Message headline="Server Error">
                          Something went wrong.
                          <br />
                          <br />
                          <Button
                            onClick={fetch}
                            color="primary"
                            variant="contained"
                          >
                            Retry
                          </Button>
                        </Message>
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
