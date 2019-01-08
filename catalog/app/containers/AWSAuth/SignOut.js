import * as React from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { connect } from 'react-redux';
import { Redirect } from 'react-router-dom';
import { createStructuredSelector } from 'reselect';

import Layout from 'components/Layout';
import Lifecycle from 'components/Lifecycle';
import Working from 'components/Working';
import AsyncResult from 'utils/AsyncResult';
import * as Config from 'utils/Config';
import { composeComponent } from 'utils/reactTools';

import { signOut } from './actions';
import msg from './messages';
import * as selectors from './selectors';


export default composeComponent('AWSAuth.SignOut',
  connect(createStructuredSelector({
    authenticated: selectors.authenticated,
    waiting: selectors.waiting,
  }), {
    doSignOut: signOut,
  }),
  ({ waiting, authenticated, doSignOut }) => (
    <Layout>
      <Working><FM {...msg.signOutWaiting} /></Working>
      <Config.Inject>
        {AsyncResult.case({
          // eslint-disable-next-line react/prop-types
          Ok: ({ signOutRedirect }) => (
            <React.Fragment>
              {!waiting && authenticated && <Lifecycle willMount={doSignOut} />}
              {!authenticated && <Redirect to={signOutRedirect} />}
            </React.Fragment>
          ),
          _: () => null,
        })}
      </Config.Inject>
    </Layout>
  ));
