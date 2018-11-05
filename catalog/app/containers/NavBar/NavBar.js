import { push } from 'connected-react-router/immutable';
import FlatButton from 'material-ui/FlatButton';
import IconMenu from 'material-ui/IconMenu';
import MenuItem from 'material-ui/MenuItem';
import TextField from 'material-ui/TextField';
import PT from 'prop-types';
import * as React from 'react';
import { Col, Row } from 'react-bootstrap';
import { connect } from 'react-redux';
import { Link, Route } from 'react-router-dom';
import * as RC from 'recompose';
import { createStructuredSelector } from 'reselect';
import styled from 'styled-components';

import MIcon from 'components/MIcon';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { authButtonStyle, backgroundColor } from 'constants/style';
import * as authSelectors from 'containers/AWSAuth/selectors';
import * as NamedRoutes from 'utils/NamedRoutes';
import { setSearchText, selectSearchText } from 'utils/SearchProvider';
import { composeComponent } from 'utils/reactTools';

import logo from 'img/logo/horizontal-white.png';


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

const Right = styled.div`
  text-align: right;
`;

export default composeComponent('NavBar',
  connect(createStructuredSelector({
    searchText: selectSearchText,
    error: authSelectors.error,
    waiting: authSelectors.waiting,
    signedIn: authSelectors.authenticated,
  })),
  RC.setPropTypes({
    dispatch: PT.func.isRequired,
    error: PT.object,
    searchText: PT.string,
    signedIn: PT.bool.isRequired,
  }),
  RC.withHandlers({
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
  }) => (
    <Bar>
      <ColNoPad xs={12} sm={6}>
        <LeftGroup {...{ handleChange, handleSearch, searchText, signedIn }} />
      </ColNoPad>
      <ColNoPad xs={12} sm={6}>
        <Route path="/signin" exact>
          {({ match }) => !match && (
            <Right>
              <UserMenu
                error={error}
                signedIn={signedIn}
                name="AWS IAM"
                waiting={waiting}
              />
            </Right>
          )}
        </Route>
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

const LeftGroup = composeComponent('NavBar.LeftGroup',
  RC.setPropTypes({
    handleChange: PT.func.isRequired,
    handleSearch: PT.func.isRequired,
    searchText: PT.string.isRequired,
    signedIn: PT.bool.isRequired,
  }),
  RC.withProps({ s3Bucket: config.aws.s3Bucket }),
  RC.withHandlers({
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
  NamedRoutes.inject(),
  ({
    handleChange,
    handleEnter,
    searchText,
    s3Bucket,
    signedIn,
    urls,
  }) => (
    <div style={{ marginTop: '16px', display: 'flex' }}>
      <Link to={urls.home()}>
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
            containerElement={<Link to={urls.browse()} />}
            label="browse"
            style={{ ...navStyle, verticalAlign: 'middle', marginLeft: '1em' }}
          />
        </React.Fragment>
      )}
    </div>
  ));

const SignIn = composeComponent('NavBar.SignIn',
  RC.setPropTypes({
    error: PT.object,
    waiting: PT.bool.isRequired,
  }),
  NamedRoutes.inject(),
  ({ error, waiting, urls }) => {
    if (waiting) {
      return <Spinner className="fa-2x" />;
    }
    return (
      <div>
        {error && (
          <MIcon
            title={`${error.message}\n${JSON.stringify(error)}`}
            style={{ verticalAlign: 'middle' }}
          >
            error_outline
          </MIcon>
        )}
        <FlatButton
          containerElement={<Link to={urls.signIn()} />}
          style={{ ...authButtonStyle, verticalAlign: 'middle' }}
        >
          Sign In
        </FlatButton>
      </div>
    );
  });

const Container = styled.div`
  margin-top: 16px;
`;

const UserMenu = composeComponent('NavBar.UserMenu',
  RC.setPropTypes({
    error: PT.object,
    signedIn: PT.bool.isRequired,
    name: PT.string,
    waiting: PT.bool.isRequired,
  }),
  // eslint-disable-next-line object-curly-newline
  ({ error, signedIn, name, waiting }) => (
    <Container>
      {signedIn
        ? <AuthMenu name={name} />
        : <SignIn error={error} waiting={waiting} />
      }
    </Container>
  ));

const MenuLink = RC.mapProps(({ to, ...rest }) => ({
  containerElement: <Link to={to} />,
  ...rest,
}))(MenuItem);

class ExtendedFlatButton extends FlatButton {
  // called by IconMenu
  setKeyboardFocus() {}
}

const AuthMenu = composeComponent('NavBar.AuthMenu',
  RC.setStatic('muiName', 'IconMenu'),
  RC.setPropTypes({
    name: PT.string,
  }),
  NamedRoutes.inject(),
  ({ name, urls }) => (
    <IconMenu
      iconButtonElement={
        <ExtendedFlatButton
          label={
            <span>
              {name} <MIcon color={authButtonStyle.color} drop="6px">expand_more</MIcon>
            </span>
          }
          style={authButtonStyle}
        />
      }
      targetOrigin={{ horizontal: 'right', vertical: 'top' }}
      anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
    >
      <MenuLink to={urls.signOut()}>Sign Out</MenuLink>
    </IconMenu>
  ));
