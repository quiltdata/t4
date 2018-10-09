import React, { Fragment } from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { connect } from 'react-redux';
import { Redirect } from 'react-router-dom';
import { createStructuredSelector } from 'reselect';

import Lifecycle from 'components/Lifecycle';
import Working from 'components/Working';
import { composeComponent } from 'utils/reactTools';

import { signOut } from './actions';
import msg from './messages';
import * as selectors from './selectors';

export default composeComponent('AWSAuth.SignOut',
  connect(createStructuredSelector({
    authenticated: selectors.authenticated,
    waiting: selectors.waiting,
    signOutRedirect: selectors.signOutRedirect,
  }), {
    doSignOut: signOut,
  }),
  ({ waiting, authenticated, signOutRedirect, doSignOut }) => (
    <Fragment>
      {!waiting && authenticated && <Lifecycle willMount={doSignOut} />}
      {!authenticated && <Redirect to={signOutRedirect} />}
      <Working><FM {...msg.signOutWaiting} /></Working>
    </Fragment>
  ));
