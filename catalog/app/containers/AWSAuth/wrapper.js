import { getLocation } from 'connected-react-router/immutable';
import memoize from 'lodash/memoize';
import { stringify } from 'query-string';
import React from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { connect } from 'react-redux';
import { Redirect } from 'react-router-dom';
import {
  branch,
  renderComponent,
} from 'recompose';
import { createStructuredSelector } from 'reselect';

import Working from 'components/Working';
import { saveProps, restoreProps, composeHOC } from 'utils/reactTools';

import msg from './messages';
import * as selectors from './selectors';

export default memoize(composeHOC('AWSAuth.Wrapper',
  saveProps(),
  connect(createStructuredSelector({
    authenticated: selectors.authenticated,
    waiting: selectors.waiting,
    location: getLocation,
  }), undefined, undefined, { pure: false }),
  branch((p) => p.waiting,
    renderComponent(() =>
      <Working><FM {...msg.wrapperWorking} /></Working>)),
  branch((p) => !p.authenticated,
    renderComponent(({ location: { pathname, search } }) =>
      <Redirect to={`/signin?${stringify({ next: pathname + search })}`} />)),
  restoreProps()));
