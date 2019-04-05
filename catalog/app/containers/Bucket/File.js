import { basename } from 'path';

import dedent from 'dedent';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { FormattedRelative } from 'react-intl';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import { unstable_Box as Box } from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardHeader from '@material-ui/core/CardHeader';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import IconButton from '@material-ui/core/IconButton';
import List from '@material-ui/core/List';
import ListItem from '@material-ui/core/ListItem';
import ListItemIcon from '@material-ui/core/ListItemIcon';
import ListItemSecondaryAction from '@material-ui/core/ListItemSecondaryAction';
import ListItemText from '@material-ui/core/ListItemText';
import Popover from '@material-ui/core/Popover';
import Typography from '@material-ui/core/Typography';
import * as colors from '@material-ui/core/colors';
import { withStyles } from '@material-ui/styles';

import ButtonIcon from 'components/ButtonIcon';
import AsyncResult from 'utils/AsyncResult';
import * as AWS from 'utils/AWS';
import Data from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import { linkStyle } from 'utils/StyledLink';
import * as RT from 'utils/reactTools';
import { getBreadCrumbs, up } from 'utils/s3paths';
import { readableBytes } from 'utils/string';
import withParsedQuery from 'utils/withParsedQuery';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import CodeButton from './CodeButton';
import FilePreview from './FilePreview';
import * as requests from './requests';
import { withSignedUrl } from './utils';


const getCrumbs = ({ bucket, path, urls }) => R.chain(
  ({ label, path: segPath }) => [
    Crumb.Segment({ label, to: urls.bucketDir(bucket, segPath) }),
    Crumb.Sep(<React.Fragment>&nbsp;/ </React.Fragment>),
  ],
  [{ label: bucket, path: '' }, ...getBreadCrumbs(up(path))],
);

const code = ({ bucket, path }) => dedent`
  import t4
  b = t4.Bucket("s3://${bucket}")
  b.fetch("${path}", "./${basename(path)}")
`;


const VersionInfo = RT.composeComponent('Bucket.File.VersionInfo',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    version: PT.string,
  }),
  RC.withStateHandlers({
    anchor: null,
    opened: false,
  }, {
    setAnchor: () => (anchor) => ({ anchor }),
    open: () => () => ({ opened: true }),
    close: () => () => ({ opened: false }),
  }),
  withStyles(({ typography }) => ({
    version: {
      ...linkStyle,
      alignItems: 'center',
      display: 'flex',
    },
    mono: {
      fontFamily: typography.monospace.fontFamily,
    },
    list: {
      width: 420,
    },
  })),
  ({
    classes,
    bucket,
    path,
    version,
    anchor,
    setAnchor,
    opened,
    open,
    close,
  }) => (
    <React.Fragment>
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions */}
      <span className={classes.version} onClick={open} ref={setAnchor}>
        {version
          ? <span className={classes.mono}>{version.substring(0, 12)}</span>
          : 'latest'
        }
        {' '}<Icon>expand_more</Icon>
      </span>
      <AWS.S3.Inject>
        {(s3) => (
          <NamedRoutes.Inject>
            {({ urls }) => (
              <Data
                fetch={requests.objectVersions}
                params={{ s3, bucket, path }}
              >
                {R.pipe(
                  AsyncResult.case({
                    Ok: (versions) => (
                      <List className={classes.list}>
                        {versions.map((v) => (
                          <ListItem
                            key={v.id}
                            button
                            onClick={close}
                            selected={version ? v.id === version : v.isLatest}
                            component={Link}
                            to={urls.bucketFile(bucket, path, v.id)}
                          >
                            <ListItemText
                              primary={
                                <span>
                                  <FormattedRelative value={v.lastModified} />
                                  {' | '}
                                  {readableBytes(v.size)}
                                  {v.isLatest && ' | latest'}
                                </span>
                              }
                              secondary={
                                <span>
                                  {v.lastModified.toLocaleString()}
                                  <br />
                                  <span className={classes.mono}>
                                    {v.id}
                                  </span>
                                </span>
                              }
                            />
                            <ListItemSecondaryAction>
                              {withSignedUrl(
                                { bucket, key: path, version: v.id },
                                (url) => (
                                  <IconButton href={url}>
                                    <Icon>arrow_downward</Icon>
                                  </IconButton>
                                ),
                              )}
                            </ListItemSecondaryAction>
                          </ListItem>
                        ))}
                      </List>
                    ),
                    Err: () => (
                      <List>
                        <ListItem>
                          <ListItemIcon><Icon>error</Icon></ListItemIcon>
                          <Typography variant="body1">
                            Error fetching versions
                          </Typography>
                        </ListItem>
                      </List>
                    ),
                    _: () => (
                      <List>
                        <ListItem>
                          <ListItemIcon>
                            <CircularProgress size={24} />
                          </ListItemIcon>
                          <Typography variant="body1">
                            Fetching versions
                          </Typography>
                        </ListItem>
                      </List>
                    ),
                  }),
                  (children) => (
                    <Popover
                      open={opened && !!anchor}
                      anchorEl={anchor}
                      onClose={close}
                      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
                      transformOrigin={{ vertical: 'top', horizontal: 'center' }}
                    >
                      {children}
                    </Popover>
                  ),
                )}
              </Data>
            )}
          </NamedRoutes.Inject>
        )}
      </AWS.S3.Inject>
    </React.Fragment>
  ));

const Meta = RT.composeComponent('Bucket.File.Meta',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    version: PT.string,
  }),
  withStyles((t) => ({
    root: {
      marginTop: t.spacing.unit * 2,
    },
    meta: {
      background: colors.lightBlue[50],
      border: [[1, 'solid', colors.lightBlue[400]]],
      borderRadius: t.shape.borderRadius,
      fontFamily: t.typography.monospace.fontFamily,
      fontSize: t.typography.body2.fontSize,
      overflow: 'auto',
      padding: t.spacing.unit,
      whiteSpace: 'pre',
    },
  })),
  ({
    classes,
    bucket,
    path,
    version,
  }) => {
    const s3 = AWS.S3.use();
    return (
      <Data
        fetch={requests.objectMeta}
        params={{ s3, bucket, path, version }}
      >
        {R.pipe(
          AsyncResult.case({
            Ok: (meta) => !!meta && !R.isEmpty(meta) && (
              <Card className={classes.root}>
                <CardHeader title="Metadata" />
                <Box px={2} pb={2}>
                  <div className={classes.meta}>
                    {JSON.stringify(meta, null, 2)}
                  </div>
                </Box>
              </Card>
            ),
            _: () => null,
          }),
        )}
      </Data>
    );
  });

export default RT.composeComponent('Bucket.File',
  withParsedQuery,
  withStyles(({ spacing: { unit }, palette }) => ({
    topBar: {
      alignItems: 'center',
      display: 'flex',
      marginBottom: 2 * unit,
    },
    nameAndVersion: {
      display: 'flex',
    },
    basename: {
      maxWidth: 500,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
    },
    at: {
      color: palette.text.secondary,
      marginLeft: unit,
      marginRight: unit,
    },
    spacer: {
      flexGrow: 1,
    },
    button: {
      marginLeft: unit,
    },
  })),
  ({
    match: { params: { bucket, path } },
    location: { query: { version } },
    classes,
  }) => (
    <React.Fragment>
      <NamedRoutes.Inject>
        {({ urls }) => (
          <BreadCrumbs
            variant="subtitle1"
            items={getCrumbs({ bucket, path, urls })}
          />
        )}
      </NamedRoutes.Inject>
      <div className={classes.topBar}>
        <Typography variant="h6" className={classes.nameAndVersion}>
          <span className={classes.basename} title={basename(path)}>
            {basename(path)}
          </span>
          <span className={classes.at}> @ </span>
          <VersionInfo bucket={bucket} path={path} version={version} />
        </Typography>
        <div className={classes.spacer} />
        <CodeButton>{code({ bucket, path })}</CodeButton>
        {withSignedUrl({ bucket, key: path, version }, (url) => (
          <Button variant="outlined" href={url} className={classes.button}>
            <ButtonIcon position="left">arrow_downward</ButtonIcon> Download
          </Button>
        ))}
      </div>
      <FilePreview handle={{ bucket, key: path, version }} />
      <Meta bucket={bucket} path={path} version={version} />
    </React.Fragment>
  ));
