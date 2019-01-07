import { push } from 'connected-react-router/immutable';
import deburr from 'lodash/deburr';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import * as RC from 'recompose';
import CircularProgress from '@material-ui/core/CircularProgress';
import Input from '@material-ui/core/Input';
import InputAdornment from '@material-ui/core/InputAdornment';
import ListItemText from '@material-ui/core/ListItemText';
import MenuItem from '@material-ui/core/MenuItem';
import MenuList from '@material-ui/core/MenuList';
import Paper from '@material-ui/core/Paper';
import Popper from '@material-ui/core/Popper';
import { MuiThemeProvider, withStyles } from '@material-ui/core/styles';

import * as style from 'constants/style';
import * as BucketConfig from 'utils/BucketConfig';
import Delay from 'utils/Delay';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Wait from 'utils/Wait';
import * as RT from 'utils/reactTools';


const withInvertedTheme =
  RT.wrap(MuiThemeProvider, () => ({ theme: style.themeInverted }));

const NavInput = RT.composeComponent('NavBar.BucketSelect.NavInput',
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

const State = RT.composeComponent('NavBar.BucketSelect.State',
  RC.setPropTypes({
    buckets: PT.array.isRequired,
    cancel: PT.func,
    children: PT.func.isRequired,
  }),
  connect(),
  NamedRoutes.inject(),
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
      setTimeout(() => {
        setAnchor(null);
        if (cancel) cancel();
      }, 300);
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
  ({ children, ...props }) => children(props));

const Styles = RT.composeComponent('NavBar.BucketSelect.Styles',
  RC.setPropTypes({
    children: PT.func.isRequired,
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
  ({ classes, children }) => children(classes));

// TODO: better placeholder styling
const Placeholder = () => <Delay>{() => <CircularProgress />}</Delay>;

export default RT.composeComponent('NavBar.BucketSelect',
  RC.setPropTypes({
    autoFocus: PT.bool,
    cancel: PT.func,
  }),
  ({ autoFocus = false, cancel }) => (
    <Wait.Placeholder fallback={() => <Placeholder />}>
      <BucketConfig.WithBucketConfigs>
        {Wait.wait((buckets) => (
          <State buckets={buckets} cancel={cancel}>
            {(state) => (
              <Styles>
                {(classes) => (
                  <React.Fragment>
                    <NavInput
                      startAdornment={<InputAdornment>s3://</InputAdornment>}
                      value={state.value}
                      className={classes.input}
                      autoFocus={autoFocus}
                      onKeyDown={state.handleKey}
                      onChange={state.handleChange}
                      onFocus={state.handleFocus}
                      onBlur={state.handleBlur}
                      placeholder=" Enter bucket name"
                    />
                    <Popper
                      open={!!state.anchor}
                      anchorEl={state.anchor}
                      placement="bottom-end"
                      className={classes.popper}
                    >
                      <Paper>
                        <MenuList>
                          {buckets.map((s) => (
                            <MenuItem
                              className={classes.item}
                              key={s.name}
                              onClick={() => state.handleSuggestion(s.name)}
                              selected={s.name === state.value}
                            >
                              <img
                                src={s.icon}
                                alt={s.title}
                                className={classes.icon}
                              />
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
                )}
              </Styles>
            )}
          </State>
        ))}
      </BucketConfig.WithBucketConfigs>
    </Wait.Placeholder>
  ));
