import { basename } from 'path';

import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import ListItem from '@material-ui/core/ListItem';
import { withStyles } from '@material-ui/core/styles';

import { S3 } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import { withData } from 'utils/Data';
import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/PlainLink';
import { composeComponent } from 'utils/reactTools';
import {
  ensureNoSlash,
  up,
  withoutPrefix,
} from 'utils/s3paths';
import { readableBytes } from 'utils/string';


const Item = composeComponent('Bucket.Tree.Listing.Item',
  RC.setPropTypes({
    icon: PT.string,
    text: PT.string,
    link: PT.string,
    children: PT.node,
  }),
  withStyles(({ spacing: { unit }, palette }) => ({
    root: {
      flexWrap: 'wrap',
      fontSize: 14, // TODO: use existing definition
      justifyContent: 'space-between',
      padding: unit,
      '&:hover': {
        background: palette.action.hover,
      },
    },
    name: {
      display: 'flex',
    },
    info: {
      display: 'flex',
    },
  })),
  // eslint-disable-next-line object-curly-newline
  ({ classes, icon, text, link, children, ...props }) => (
    <ListItem
      component={link ? Link : undefined}
      to={link}
      className={classes.root}
      {...props}
    >
      <div className={classes.name}>
        {!!icon && <Icon style={{ fontSize: 16, marginRight: 4 }}>{icon}</Icon>}
        {text}
      </div>
      <div className={classes.info}>{children}</div>
    </ListItem>
  ));

const ItemDir = composeComponent('Bucket.Tree.Listing.ItemDir',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    name: PT.string.isRequired,
  }),
  NamedRoutes.inject(),
  ({ bucket, path, name, urls }) => (
    <Item
      icon="folder_open"
      text={name}
      link={urls.bucketTree(bucket, path)}
    />
  ));

const ItemFile = composeComponent('Bucket.Tree.Listing.ItemFile',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
    modified: PT.instanceOf(Date).isRequired,
    size: PT.number.isRequired,
  }),
  NamedRoutes.inject(),
  withStyles(() => ({
    size: {
      textAlign: 'right',
      width: '6em',
    },
    modified: {
      textAlign: 'right',
      width: '12em',
    },
  })),
  // eslint-disable-next-line object-curly-newline
  ({ classes, bucket, path, size, modified, urls }) => (
    <Item
      icon="insert_drive_file"
      text={basename(path)}
      link={urls.bucketTree(bucket, path)}
    >
      <div className={classes.size}>{readableBytes(size)}</div>
      <div className={classes.modified}>{modified.toLocaleString()}</div>
    </Item>
  ));

const Stats = composeComponent('Bucket.Tree.Listing.Stats',
  RC.setPropTypes({
    files: PT.array.isRequired,
  }),
  RC.withProps(({ files }) =>
    files.reduce((sum, file) => ({
      files: sum.files + 1,
      size: sum.size + file.size,
      modified: file.modified > sum.modified ? file.modified : sum.modified,
    }), {
      files: 0,
      size: 0,
      modified: 0,
    })),
  withStyles(({ palette, spacing: { unit } }) => ({
    root: {
      background: palette.grey[100],
      display: 'flex',
      flexWrap: 'wrap',
      justifyContent: 'space-between',
      padding: unit,
    },
  })),
  ({ classes, files, size, modified }) => (
    <div className={classes.root}>
      <span>{files} files / {readableBytes(size)}</span>
      {!!modified && (
        <span>Last modified {modified.toLocaleString()}</span>
      )}
    </div>
  ));

const mkHandle = (bucket) => (i) => ({
  bucket,
  key: i.Key,
  modified: i.LastModified,
  size: i.Size,
  etag: i.ETag,
});

const fetchData = async ({ s3, bucket, path }) => {
  const data = await s3.listObjectsV2({
    Bucket: bucket,
    Delimiter: '/',
    Prefix: path,
  }).promise();

  const directories = R.pipe(
    R.pluck('Prefix'),
    R.filter((d) => d !== '/' && d !== '../'),
    R.uniq,
  )(data.CommonPrefixes);

  const files = data.Contents
    .map(mkHandle(bucket))
    // filter-out "directory-files" (files that match prefixes)
    .filter((f) => f.key !== path && !f.key.endsWith('/'));

  return { files, directories, bucket, path };
};

export default composeComponent('Bucket.Tree.Listing',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
  }),
  S3.inject(),
  withData({
    params: R.pick(['s3', 'bucket', 'path']),
    fetch: fetchData,
  }),
  withStyles(({ spacing: { unit }, palette }) => ({
    root: {
      minHeight: 40 + (4 * unit), // for spinner
      padding: '0 !important',
      position: 'relative',
    },
    lock: {
      alignItems: 'center',
      background: palette.common.white,
      display: 'flex',
      height: '100%',
      justifyContent: 'center',
      left: 0,
      opacity: 0.5,
      padding: 2 * unit,
      position: 'absolute',
      top: 0,
      width: '100%',
      zIndex: 1,
    },
  })),
  RC.withHandlers({
    // eslint-disable-next-line react/prop-types
    renderOk: () => ({ bucket, path, directories, files }) => (
      <React.Fragment>
        <Stats files={files} />
        {path !== '' && <ItemDir bucket={bucket} path={up(path)} name=".." />}
        {directories.map((d) => (
          <ItemDir
            bucket={bucket}
            key={d}
            path={d}
            name={ensureNoSlash(withoutPrefix(path, d))}
          />
        ))}
        {files.map(({ key, modified, size }) => (
          <ItemFile
            bucket={bucket}
            key={key}
            path={key}
            size={size}
            modified={modified}
          />
        ))}
      </React.Fragment>
    ),
    renderErr: () => () => (
      // TODO: proper error display, retry
      <h1>Error</h1>
    ),
    renderLock: ({ classes }) => () => (
      <div className={classes.lock}>
        <CircularProgress />
      </div>
    ),
  }),
  ({ classes, renderOk, renderErr, renderLock, data: { result } }) => (
    <Card>
      <CardContent className={classes.root}>
        {AsyncResult.case({
          Pending: renderLock,
          Init: renderLock,
          _: () => null,
        }, result)}
        {AsyncResult.case({
          Ok: renderOk,
          Err: renderErr,
          Pending: AsyncResult.case({
            Ok: renderOk,
            Err: renderErr,
            _: () => null,
          }),
          _: () => null,
        }, result)}
      </CardContent>
    </Card>
  ));
