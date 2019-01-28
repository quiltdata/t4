import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import ListItem from '@material-ui/core/ListItem';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import AsyncResult from 'utils/AsyncResult';
import { composeComponent } from 'utils/reactTools';
import { readableBytes } from 'utils/string';
import tagged from 'utils/tagged';

import { displayError } from './errors';


export const ListingItem = tagged([
  'Dir', // { name, to }
  'File', // { name, to, size, modified }
]);

const Item = composeComponent('Bucket.Listing.Item',
  RC.setPropTypes({
    icon: PT.string,
    name: PT.string.isRequired,
    to: PT.string.isRequired,
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
      alignItems: 'center',
      display: 'flex',
    },
    info: {
      display: 'flex',
    },
    icon: {
      fontSize: 16, // TODO: use predefined font-size
      marginRight: 0.5 * unit,
    },
  })),
  // eslint-disable-next-line object-curly-newline
  ({ classes, name, to, icon, children, ...props }) => (
    <ListItem
      component={Link}
      to={to}
      className={classes.root}
      {...props}
    >
      <div className={classes.name}>
        {!!icon && <Icon className={classes.icon}>{icon}</Icon>}
        {name}
      </div>
      <div className={classes.info}>{children}</div>
    </ListItem>
  ));

const computeStats = R.reduce(ListingItem.reducer({
  File: (file) => R.evolve({
    files: R.inc,
    size: R.add(file.size),
    modified: R.max(file.modified),
  }),
  Dir: () => R.evolve({
    dirs: R.inc,
  }),
}), {
  dirs: 0,
  files: 0,
  size: 0,
  modified: 0,
});

const Stats = composeComponent('Bucket.Listing.Stats',
  RC.setPropTypes({
    items: PT.array.isRequired,
  }),
  withStyles(({ palette, spacing: { unit } }) => ({
    root: {
      background: palette.grey[100],
      display: 'flex',
      flexWrap: 'wrap',
      padding: unit,
    },
    divider: {
      color: palette.text.hint,
      marginLeft: unit,
      marginRight: unit,
    },
    spacer: {
      flexGrow: 1,
    },
  })),
  ({ classes, items }) => {
    const stats = computeStats(items);
    return (
      <div className={classes.root}>
        <span>{stats.dirs} folders</span>
        <span className={classes.divider}> | </span>
        <span>{stats.files} files</span>
        <span className={classes.divider}> | </span>
        <span>{readableBytes(stats.size)}</span>
        <span className={classes.spacer} />
        {!!stats.modified && (
          <span>Last modified {stats.modified.toLocaleString()}</span>
        )}
      </div>
    );
  });

export default composeComponent('Bucket.Listing',
  RC.setPropTypes({
    // AsyncResult of ListingItems
    result: PT.object.isRequired,
    whenEmpty: PT.func,
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
    empty: {
      marginLeft: 2 * unit,
      paddingTop: 2.5 * unit,
    },
    size: {
      textAlign: 'right',
      width: '6em',
    },
    modified: {
      textAlign: 'right',
      width: '12em',
    },
  })),
  RC.withHandlers({
    // eslint-disable-next-line react/prop-types
    renderOk: ({ classes }) => R.ifElse(R.isEmpty,
      () => (
        <Typography className={classes.empty} variant="h5">
          No files
        </Typography>
      ),
      (items) => (
        <React.Fragment>
          <Stats items={items} />
          {items.map(ListingItem.case({
            // eslint-disable-next-line react/prop-types
            Dir: ({ name, to }) => (
              <Item
                icon="folder_open"
                key={name}
                name={name}
                to={to}
              />
            ),
            // eslint-disable-next-line react/prop-types
            File: ({ name, to, size, modified }) => (
              <Item
                icon="insert_drive_file"
                key={name}
                name={name}
                to={to}
              >
                <div className={classes.size}>{readableBytes(size)}</div>
                {!!modified && (
                  <div className={classes.modified}>{modified.toLocaleString()}</div>
                )}
              </Item>
            ),
          }))}
        </React.Fragment>
      )),
    renderLock: ({ classes }) => () => (
      <div className={classes.lock}>
        <CircularProgress />
      </div>
    ),
  }),
  RC.branch(
    ({ whenEmpty, result }) =>
      whenEmpty && AsyncResult.Ok.is(result, R.isEmpty),
    RC.renderComponent(({ whenEmpty }) => whenEmpty()),
  ),
  ({ result, classes, renderOk, renderLock }) => (
    <Card>
      <CardContent className={classes.root}>
        {AsyncResult.case({
          Pending: renderLock,
          Init: renderLock,
          _: () => null,
        }, result)}
        {AsyncResult.case({
          Ok: renderOk,
          Err: displayError(),
          Pending: AsyncResult.case({
            Ok: renderOk,
            _: () => null,
          }),
          _: () => null,
        }, result)}
      </CardContent>
    </Card>
  ));
