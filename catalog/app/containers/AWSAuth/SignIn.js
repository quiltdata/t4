import get from 'lodash/fp/get';
import React from 'react';
import { FormattedMessage as FM } from 'react-intl';
import { connect } from 'react-redux';
import { Redirect } from 'react-router-dom';
import { branch, renderComponent } from 'recompose';
import { reduxForm, Field, SubmissionError } from 'redux-form/immutable';
import { createStructuredSelector } from 'reselect';

import * as Config from 'utils/Config';
import * as Wait from 'utils/Wait';
import defer from 'utils/defer';
import { captureError } from 'utils/errorReporting';
import { composeComponent } from 'utils/reactTools';
import * as validators from 'utils/validators';
import withParsedQuery from 'utils/withParsedQuery';

import { signIn } from './actions';
import * as errors from './errors';
import msg from './messages';
import * as selectors from './selectors';
import * as Layout from './Layout';


const Container = Layout.mkLayout(<FM {...msg.signInHeading} />);

export default composeComponent('AWSAuth.SignIn',
  connect(createStructuredSelector({
    authenticated: selectors.authenticated,
  })),
  reduxForm({
    form: 'AWSAuth.SignIn',
    onSubmit: async (values, dispatch) => {
      const result = defer();
      dispatch(signIn(values.toJS(), result.resolver));
      try {
        await result.promise;
      } catch (e) {
        if (e instanceof errors.InvalidCredentials) {
          throw new SubmissionError({ _error: 'invalidCredentials' });
        }
        captureError(e);
        throw new SubmissionError({ _error: 'unexpected' });
      }
    },
  }),
  withParsedQuery,
  branch(get('authenticated'),
    renderComponent(({ location: { query } }) => (
      <Config.Inject>
        {Wait.wait(({ signInRedirect }) => (
          <Redirect to={query.next || signInRedirect} />
        ))}
      </Config.Inject>
    ))),
  ({ handleSubmit, submitting, submitFailed, invalid, error }) => (
    <Container>
      <form onSubmit={handleSubmit}>
        <Field
          component={Layout.Field}
          name="accessKeyId"
          validate={[validators.required]}
          disabled={submitting}
          floatingLabelText={<FM {...msg.signInAccessKeyID} />}
          errors={{
            required: <FM {...msg.signInAccessKeyIDRequired} />,
          }}
        />
        <Field
          component={Layout.Field}
          name="secretAccessKey"
          type="password"
          validate={[validators.required]}
          disabled={submitting}
          floatingLabelText={<FM {...msg.signInSecretAccessKey} />}
          errors={{
            required: <FM {...msg.signInSecretAccessKeyRequired} />,
          }}
        />
        <Layout.Error
          {...{ submitFailed, error }}
          errors={{
            invalidCredentials: <FM {...msg.signInErrorInvalidCredentials} />,
            unexpected: <FM {...msg.signInErrorUnexpected} />,
          }}
        />
        <Layout.Actions>
          <Layout.Submit
            label={<FM {...msg.signInSubmit} />}
            disabled={submitting || (submitFailed && invalid)}
            busy={submitting}
          />
        </Layout.Actions>
      </form>
    </Container>
  ));
