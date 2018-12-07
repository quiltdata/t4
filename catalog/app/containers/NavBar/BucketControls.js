import cx from 'classnames';
import { push } from 'connected-react-router/immutable';
import deburr from 'lodash/deburr';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import { Route } from 'react-router-dom';
import * as RC from 'recompose';
import { createStructuredSelector } from 'reselect';
import Button from '@material-ui/core/Button';
import Icon from '@material-ui/core/Icon';
import Input from '@material-ui/core/Input';
import InputBase from '@material-ui/core/InputBase';
import InputAdornment from '@material-ui/core/InputAdornment';
import ListItemText from '@material-ui/core/ListItemText';
import MenuItem from '@material-ui/core/MenuItem';
import MenuList from '@material-ui/core/MenuList';
import Paper from '@material-ui/core/Paper';
import Popper from '@material-ui/core/Popper';
import { MuiThemeProvider, withStyles } from '@material-ui/core/styles';
import { fade } from '@material-ui/core/styles/colorManipulator';

import * as style from 'constants/style';
import * as BucketConfig from 'containers/Bucket/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import { setSearchText, selectSearchText } from 'utils/SearchProvider';
import * as RT from 'utils/reactTools';


const withInvertedTheme =
  RT.wrap(MuiThemeProvider, () => ({ theme: style.themeInverted }));

const BucketDisplay = RT.composeComponent('NavBar.BucketControls.BucketDisplay',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    select: PT.func.isRequired,
  }),
  withStyles(() => ({
    root: {
      textTransform: 'none !important',
    },
    s3: {
      opacity: 0.7,
    },
    bucket: {
      maxWidth: 320,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
    },
  })),
  ({ classes, bucket, select }) => (
    <Button
      color="inherit"
      className={classes.root}
      onClick={select}
    >
      <span className={classes.s3}>s3://</span>
      <span className={classes.bucket}>{bucket}</span>
      <Icon>expand_more</Icon>
    </Button>
  ));

const normalizeBucket = R.pipe(
  deburr,
  R.toLower,
  R.replace(/^[^a-z0-9]/g, ''),
  R.replace(/[^a-z0-9-.]/g, '-'),
);

const getCycled = (getter) => (arr, val, offset) => {
  const index = arr.findIndex(R.pipe(getter, R.equals(val))) + offset;
  const cycledIndex = ((index + 1 + arr.length + 1) % (arr.length + 1)) - 1;
  return getter(arr[cycledIndex]);
};

const getBucketCycled = getCycled(R.prop('name'));

const BucketSelect = RT.composeComponent('NavBar.BucketControls.BucketSelect',
  RC.setPropTypes({
    bucket: PT.string,
    cancel: PT.func,
    autoFocus: PT.bool,
  }),
  connect(),
  NamedRoutes.inject(),
  RT.consume(BucketConfig.BucketsCtx, (buckets, props) => ({
    ...props,
    buckets: buckets.filter((b) => b.menu),
  })),
  RC.withStateHandlers({
    value: '',
    anchor: null,
  }, {
    setValue: () => (value) => ({ value }),
    nextSuggestion: ({ value }, { buckets }) => () => ({
      value: getBucketCycled(buckets, value, 1) || '',
    }),
    prevSuggestion: ({ value }, { buckets }) => () => ({
      value: getBucketCycled(buckets, value, -1) || '',
    }),
    setAnchor: () => (anchor) => ({ anchor }),
  }),
  RC.withHandlers({
    go: ({ bucket, urls, dispatch, cancel }) => (to) => {
      if (to && bucket !== to) {
        dispatch(push(urls.bucketRoot(to)));
      }
      if (cancel) cancel();
    },
    handleChange: ({ setValue }) => (evt) => {
      setValue(normalizeBucket(evt.target.value));
    },
    handleFocus: ({ setAnchor }) => (evt) => {
      setAnchor(evt.target);
    },
    handleBlur: ({ setAnchor, cancel }) => () => {
      setAnchor(null);
      if (cancel) cancel();
    },
  }),
  RC.withHandlers({
    handleKey: ({
      anchor,
      go,
      value,
      nextSuggestion,
      prevSuggestion,
    }) => (evt) => {
      // eslint-disable-next-line default-case
      switch (evt.key) {
        case 'Enter':
          go(value);
          break;
        case 'Escape':
          if (anchor) anchor.blur();
          break;
        case 'ArrowUp':
          prevSuggestion();
          break;
        case 'ArrowDown':
        case 'Tab':
          // prevent Tab from switching focus
          evt.preventDefault();
          nextSuggestion();
          break;
      }
    },
    handleSuggestion: ({ go, setValue }) => (s) => {
      setValue(s);
      go(s);
    },
  }),
  withStyles(({ spacing: { unit }, zIndex }) => ({
    input: {
      marginLeft: unit * 2,
    },
    popper: {
      zIndex: zIndex.appBar + 1,
    },
    item: {
      paddingBottom: 20,
      paddingTop: 20,
    },
    description: {
      maxWidth: 50 * unit,
    },
    icon: {
      height: 40,
      width: 40,
    },
    help: {
      paddingLeft: 2 * unit,
      paddingTop: unit,
    },
  })),
  ({
    anchor,
    autoFocus = false,
    value,
    handleKey,
    handleChange,
    buckets,
    handleSuggestion,
    handleFocus,
    handleBlur,
    classes,
  }) => (
    <React.Fragment>
      <NavInput
        startAdornment={<InputAdornment>s3://</InputAdornment>}
        value={value}
        className={classes.input}
        autoFocus={autoFocus}
        onKeyDown={handleKey}
        onChange={handleChange}
        onFocus={handleFocus}
        onBlur={handleBlur}
        placeholder=" Enter bucket name"
      />
      <Popper
        open={!!anchor}
        anchorEl={anchor}
        placement="bottom-end"
        className={classes.popper}
      >
        <Paper>
          <MenuList>
            {buckets.map((s) => (
              <MenuItem
                className={classes.item}
                key={s.name}
                onMouseDown={() => handleSuggestion(s.name)}
                selected={s.name === value}
              >
                <img src={s.icon} alt={s.title} className={classes.icon} />
                <ListItemText
                  primary={s.title}
                  secondary={s.description}
                  secondaryTypographyProps={{
                    noWrap: true,
                    className: classes.description,
                  }}
                  title={s.description}
                />
              </MenuItem>
            ))}
            <li className={classes.help}>
              <a href="https://github.com/quiltdata/t4/tree/master/deployment#installation">
                Learn how to create your own registry
              </a>
            </li>
          </MenuList>
        </Paper>
      </Popper>
    </React.Fragment>
  ));

const NavInput = RT.composeComponent('NavBar.BucketControls.NavInput',
  withInvertedTheme,
  withStyles(({ palette }) => ({
    underline: {
      '&:after': {
        borderBottomColor: palette.secondary.main,
      },
    },
    input: {
      textOverflow: 'ellipsis',
    },
  })),
  Input);

const Search = RT.composeComponent('NavBar.BucketControls.Search',
  RC.setPropTypes({
    bucket: PT.string.isRequired,
    disabled: PT.bool,
  }),
  connect(createStructuredSelector({
    searchText: selectSearchText,
  })),
  NamedRoutes.inject(),
  RC.withHandlers({
    handleChange: ({ dispatch }) => (evt) => {
      dispatch(setSearchText(evt.target.value));
    },
    handleEnter: ({ dispatch, urls, bucket, searchText }) => (evt) => {
      if (evt.key === 'Enter') {
        /* suppress onSubmit (didn't actually find this to be a problem tho) */
        evt.preventDefault();
        // TODO: check out if encodeURIComponent is required
        dispatch(push(urls.bucketSearch(bucket, encodeURIComponent(searchText))));
      }
    },
  }),
  withStyles(({ shape: { borderRadius }, spacing: { unit }, palette }) => ({
    root: {
      background: fade(palette.common.white, 0.9),
      borderRadius,
      marginLeft: 2 * unit,
      minWidth: 240,
      '&:not($disabled):hover': {
        background: palette.common.white,
      },
    },
    disabled: {
      opacity: 0.8,
    },
    focused: {
      background: palette.common.white,
    },
    input: {
      paddingLeft: 4 * unit,
      textOverflow: 'ellipsis',
    },
    adornment: {
      justifyContent: 'center',
      pointerEvents: 'none',
      position: 'absolute',
      width: 4 * unit,
    },
  })),
  ({
    classes: { adornment, disabled: disabledCls, ...classes },
    handleChange,
    handleEnter,
    searchText,
    disabled = false,
  }) => (
    <InputBase
      startAdornment={
        <InputAdornment className={adornment}>
          <Icon>search</Icon>
        </InputAdornment>
      }
      classes={classes}
      className={cx({ [disabledCls]: disabled })}
      placeholder="Search"
      onChange={handleChange}
      onKeyPress={handleEnter}
      value={disabled ? 'Search not available' : searchText}
      disabled={disabled}
    />
  ));

export default RT.composeComponent('NavBar.BucketControls',
  NamedRoutes.inject(),
  RC.withStateHandlers({
    selecting: false,
  }, {
    select: () => () => ({ selecting: true }),
    cancel: () => () => ({ selecting: false }),
  }),
  withStyles(({ palette }) => ({
    root: {
      alignItems: 'center',
      display: 'flex',
    },
    button: {
      borderColor: fade(palette.common.white, 0.23),
    },
  })),
  ({
    classes,
    paths,
    selecting,
    select,
    cancel,
  }) => (
    <div className={classes.root}>
      <Route path={paths.bucketRoot}>
        {({ match }) =>
          match
            ? (
              <React.Fragment>
                {selecting
                  ? (
                    <BucketSelect
                      autoFocus
                      bucket={match.params.bucket}
                      cancel={cancel}
                    />
                  )
                  : <BucketDisplay bucket={match.params.bucket} select={select} />
                }
                <BucketConfig.CurrentCtx.Consumer>
                  {(current) => (
                    <Search
                      bucket={match.params.bucket}
                      disabled={!current || !current.searchEndpoint}
                    />
                  )}
                </BucketConfig.CurrentCtx.Consumer>
              </React.Fragment>
            )
            : <BucketSelect />
        }
      </Route>
    </div>
  ));
