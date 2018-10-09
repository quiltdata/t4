import { defineMessages } from 'react-intl';

const scope = 'app.containers.AWSAuth';

export default defineMessages({
  notificationAuthLost: {
    id: `${scope}.notificationAuthLost`,
    defaultMessage: 'Authentication lost. Sign in again.',
  },

  // Wrapper
  wrapperWorking: {
    id: `${scope}.Wrapper.working`,
    defaultMessage: 'Authenticating...',
  },

  // SignIn
  signInHeading: {
    id: `${scope}.SignIn.heading`,
    defaultMessage: 'Sign in with IAM',
  },
  signInAccessKeyID: {
    id: `${scope}.SignIn.accessKeyID`,
    defaultMessage: 'Access Key ID',
  },
  signInAccessKeyIDRequired: {
    id: `${scope}.SignIn.accessKeyIDRequired`,
    defaultMessage: 'Enter your Access Key ID',
  },
  signInSecretAccessKey: {
    id: `${scope}.SignIn.secretAccessKey`,
    defaultMessage: 'Secret Access Key',
  },
  signInSecretAccessKeyRequired: {
    id: `${scope}.SignIn.secretAccessKeyRequired`,
    defaultMessage: 'Enter your Secret Access Key',
  },
  signInSubmit: {
    id: `${scope}.SignIn.submit`,
    defaultMessage: 'Sign in',
  },
  signInErrorInvalidCredentials: {
    id: `${scope}.SignIn.errorInvalidCredentials`,
    defaultMessage: 'Invalid credentials',
  },
  signInErrorUnexpected: {
    id: `${scope}.SignIn.errorUnexpected`,
    defaultMessage: 'Something went wrong. Try again later.',
  },

  // SignOut
  signOutWaiting: {
    id: `${scope}.SignOut.waiting`,
    defaultMessage: 'Signing out',
  },
});
