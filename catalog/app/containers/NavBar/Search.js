import cx from 'classnames';
import { push } from 'connected-react-router/immutable';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { connect } from 'react-redux';
import * as RC from 'recompose';
import { createStructuredSelector } from 'reselect';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';
import InputAdornment from '@material-ui/core/InputAdornment';
import InputBase from '@material-ui/core/InputBase';
import { withStyles } from '@material-ui/core/styles';
import { fade } from '@material-ui/core/styles/colorManipulator';

import * as BucketConfig from 'utils/BucketConfig';
import Delay from 'utils/Delay';
import * as NamedRoutes from 'utils/NamedRoutes';
import { setSearchText, selectSearchText } from 'utils/SearchProvider';
import * as Wait from 'utils/Wait';
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
        dispatch(push(urls.bucketSearch(bucket, searchText)));
      }
    },
  }),
  ({ children, ...props }) =>
    children(R.pick(['searchText', 'handleChange', 'handleEnter'], props)));

const fallback = () => <Delay>{() => <CircularProgress />}</Delay>;

export default RT.composeComponent('NavBar.Search', () => (
  <Wait.Placeholder fallback={fallback}>
    <BucketConfig.WithCurrentBucketConfig>
      {Wait.wait(({ name, searchEndpoint }) => searchEndpoint
        ? (
          <State bucket={name}>
            {({ searchText, handleChange, handleEnter }) => (
              <SearchBox
                value={searchText}
                onChange={handleChange}
                onKeyPress={handleEnter}
              />
            )}
          </State>
        )
        : <SearchBox disabled value="Search not available" />)}
    </BucketConfig.WithCurrentBucketConfig>
  </Wait.Placeholder>
));
