import cx from 'classnames';
import { push } from 'connected-react-router/immutable';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import { Route } from 'react-router-dom';
import * as RC from 'recompose';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import InputAdornment from '@material-ui/core/InputAdornment';
import InputBase from '@material-ui/core/InputBase';
import { withStyles } from '@material-ui/styles';
import { fade } from '@material-ui/core/styles/colorManipulator';

import * as BucketConfig from 'utils/BucketConfig';
import Delay from 'utils/Delay';
import * as NamedRoutes from 'utils/NamedRoutes';
import * as Wait from 'utils/Wait';
import parse from 'utils/parseSearch';
import * as RT from 'utils/reactTools';


const Styles = RT.composeComponent('NavBar.Search.Styles',
  RC.setPropTypes({
    children: PT.func.isRequired,
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
  ({ classes, children }) => children(classes));

const SearchBox = RT.composeComponent('NavBar.Search.SearchBox',
  ({ disabled, ...props }) => (
    <Styles>
      {({ adornment, disabled: disabledCls, ...classes }) => (
        <InputBase
          startAdornment={
            <InputAdornment className={adornment}>
              <Icon>search</Icon>
            </InputAdornment>
          }
          classes={classes}
          className={cx({ [disabledCls]: disabled })}
          placeholder="Search"
          disabled={disabled}
          {...props}
        />
      )}
    </Styles>
  ));

const State = RT.composeComponent('NavBar.Search.State',
  RC.setPropTypes({
    children: PT.func.isRequired,
    bucket: PT.string.isRequired,
    query: PT.string.isRequired,
  }),
  connect(undefined, undefined, undefined, { pure: false }),
  NamedRoutes.inject(),
  RC.withStateHandlers({
    value: null,
  }, {
    focus: (_state, { query }) => () => ({ value: query }),
    blur: () => () => ({ value: null }),
    change: () => (value) => ({ value }),
  }),
  RC.withHandlers({
    onChange: ({ change }) => (evt) => {
      change(evt.target.value);
    },
    onKeyDown: ({ dispatch, urls, bucket, value, query }) => (evt) => {
      // eslint-disable-next-line default-case
      switch (evt.key) {
        case 'Enter':
          /* suppress onSubmit (didn't actually find this to be a problem tho) */
          evt.preventDefault();
          if (query !== value) {
            dispatch(push(urls.bucketSearch(bucket, value)));
          }
          evt.target.blur();
          break;
        case 'Escape':
          evt.target.blur();
          break;
      }
    },
    onFocus: ({ focus }) => () => {
      focus();
    },
    onBlur: ({ blur }) => () => {
      blur();
    },
  }),
  ({ children, value, query, ...props }) => children({
    value: value === null ? query : value,
    ...R.pick(['onChange', 'onKeyDown', 'onFocus', 'onBlur'], props),
  }));

const fallback = () => <Delay>{() => <CircularProgress />}</Delay>;

const WithQuery = RT.composeComponent('NavBar.Search.WithQuery',
  RC.setPropTypes({
    children: PT.func.isRequired,
  }),
  ({ children }) => (
    <NamedRoutes.Inject>
      {({ paths }) => (
        <Route path={paths.bucketSearch}>
          {({ location: l, match }) => children((match && parse(l.search).q) || '')}
        </Route>
      )}
    </NamedRoutes.Inject>
  ));

export default RT.composeComponent('NavBar.Search', () => (
  <Wait.Placeholder fallback={fallback}>
    <BucketConfig.WithCurrentBucketConfig>
      {Wait.wait(({ name, searchEndpoint }) => searchEndpoint
        ? (
          <WithQuery>
            {(query) => (
              <State bucket={name} query={query}>
                {(state) => <SearchBox {...state} />}
              </State>
            )}
          </WithQuery>
        )
        : <SearchBox disabled value="Search not available" />)}
    </BucketConfig.WithCurrentBucketConfig>
  </Wait.Placeholder>
));
