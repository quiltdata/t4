/* AuthBar - app wide navigation bar and user controls */
import FlatButton from 'material-ui/FlatButton';
import TextField from 'material-ui/TextField';
import PropTypes from 'prop-types';
import React from 'react';
import { Col, Row } from 'react-bootstrap';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import { push } from 'react-router-redux';
import {
  setPropTypes,
  withHandlers,
  withProps,
} from 'recompose';
import { createStructuredSelector } from 'reselect';
import styled from 'styled-components';

import logo from 'img/logo/horizontal-white.png';

import { backgroundColor } from 'constants/style';
// import { blog, company, docs, jobs } from 'constants/urls';
import { setSearchText } from 'containers/App/actions';
import { selectSearchText } from 'containers/App/selectors';
import * as authSelectors from 'containers/AWSAuth/selectors';
import UserMenu from 'components/UserMenu';
import { composeComponent } from 'utils/reactTools';

import config from 'constants/config';

const Bar = styled(Row)`
  background-color: ${backgroundColor};
  color: white;
  padding: 0 16px 16px 16px
`;

const ColNoPad = styled(Col)`
  padding: 0;
`;

const navStyle = {
  color: '#ddd',
};

/*
const NavRow = styled(Row)`
  background-color: rgb(0, 0, 0);
  border-bottom: 1px solid rgb(24, 24, 24);
  margin-left: -16px;
  margin-right: -16px;
`;
*/

const Right = styled.div`
  text-align: right;
`;

export default composeComponent('AuthBar',
  connect(createStructuredSelector({
    searchText: selectSearchText,
    error: authSelectors.error,
    waiting: authSelectors.waiting,
    signedIn: authSelectors.authenticated,
  })),
  setPropTypes({
    dispatch: PropTypes.func.isRequired,
    error: PropTypes.object,
    searchText: PropTypes.string,
    signedIn: PropTypes.bool.isRequired,
    showUserMenu: PropTypes.bool,
  }),
  withHandlers({
    handleSearch: ({ dispatch }) => (query) => {
      // submit search via query param to the search results page
      dispatch(push(`/search/?q=${encodeURIComponent(query)}`));
    },
    handleChange: ({ dispatch }) => (text) => {
      dispatch(setSearchText(text));
    },
  }),
  ({
    error,
    waiting,
    searchText,
    signedIn,
    handleChange,
    handleSearch,
    showUserMenu = true,
  }) => (
    <Bar>
      {/*
      <NavRow>
        <Right>
          <FlatButton href={docs} label="docs" style={navStyle} />
          <FlatButton
            containerElement={<Link to="/browse/" />}
            label="browse"
            style={{ ...navStyle, verticalAlign: 'middle' }}
          />
          {config.team ? null : (
            <Fragment>
              <FlatButton
                containerElement={<Link to="/#pricing" />}
                label="pricing"
                style={{ ...navStyle, verticalAlign: 'middle' }}
              />
              <FlatButton href={jobs} label="jobs" style={navStyle} />
            </Fragment>
          )}
          <FlatButton href={blog} label="blog" style={navStyle} />
          <FlatButton href={company} label="about" style={navStyle} />
        </Right>
      </NavRow>
      */}
      <ColNoPad xs={12} sm={6} smPush={6}>
        {showUserMenu && (
          <Right>
            <UserMenu
              error={error}
              signedIn={signedIn}
              name="AWS IAM"
              waiting={waiting}
            />
          </Right>
        )}
      </ColNoPad>
      <ColNoPad xs={12} sm={6} smPull={6}>
        <LeftGroup {...{ handleChange, handleSearch, searchText, signedIn }} />
      </ColNoPad>
    </Bar>
  ));


const Lockup = styled.div`
  display: inline-block;
  margin-right: 16px;
  > img {
    height: 36px;
  }
  vertical-align: top;
`;

const hintStyle = {
  bottom: '6px',
  color: '#888',
};

const inputStyle = {
  color: '#444',
};

const searchStyle = {
  backgroundColor: 'rgba(255, 255, 255, .9)',
  borderRadius: '4px',
  fontSize: '15px',
  height: '36px',
  paddingLeft: '8px',
  paddingRight: '8px',
  width: 'calc(100% - 140px)',
};

const LeftGroup = composeComponent('AuthBar.LeftGroup',
  setPropTypes({
    handleChange: PropTypes.func.isRequired,
    handleSearch: PropTypes.func.isRequired,
    searchText: PropTypes.string.isRequired,
    signedIn: PropTypes.bool.isRequired,
  }),
  withProps({ s3Bucket: config.aws.s3Bucket }),
  withHandlers({
    // eslint will cry about evt but we need the second positional arg
    // eslint-disable-next-line no-unused-vars
    handleChange: ({ handleChange }) => (_evt, text) => {
      handleChange(text);
    },
    handleEnter: ({ handleSearch, searchText }) => (evt) => {
      if (evt.key === 'Enter') {
        /* suppress onSubmit (didn't actually find this to be a problem tho) */
        evt.preventDefault();
        handleSearch(searchText);
      }
    },
  }),
  ({ handleChange, handleEnter, searchText, s3Bucket, signedIn }) => (
    <div style={{ marginTop: '16px', display: 'flex' }}>
      <Link to="/">
        <Lockup>
          <img alt="Quilt logo" src={logo} />
        </Lockup>
      </Link>
      {signedIn && (
        <React.Fragment>
          <TextField
            hintStyle={hintStyle}
            hintText={`Search s3:${s3Bucket}`}
            inputStyle={inputStyle}
            onChange={handleChange}
            onKeyPress={handleEnter}
            style={searchStyle}
            underlineShow={false}
            value={searchText}
          />
          <FlatButton
            containerElement={<Link to="/browse/" />}
            label="browse"
            style={{ ...navStyle, verticalAlign: 'middle', marginLeft: '1em' }}
          />
        </React.Fragment>
      )}
    </div>
  ));
