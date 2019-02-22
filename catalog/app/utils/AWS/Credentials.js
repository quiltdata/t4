import 'aws-sdk/lib/credentials';
import AWS from 'aws-sdk/lib/core';
import * as React from 'react';
import * as reduxHook from 'redux-react-hook';

import * as Auth from 'containers/Auth';
import * as APIConnector from 'utils/APIConnector';
import * as Config from 'utils/Config';
import useMemoEq from 'utils/useMemoEq';


class RegistryCredentials extends AWS.Credentials {
  constructor({ req }) {
    super();
    this.req = req;
  }

  refresh(callback) {
    if (!this.refreshing) {
      this.refreshing = this.req({ endpoint: '/auth/get_credentials' })
        .then((data) => {
          this.expireTime = new Date(data.Expiration);
          this.accessKeyId = data.AccessKeyId;
          this.secretAccessKey = data.SecretAccessKey;
          this.sessionToken = data.SessionToken;
          delete this.refreshing;
          if (callback) callback();
        })
        .catch((e) => {
          delete this.refreshing;
          if (callback) callback(e);
          throw e;
        });
    }
    return this.refreshing;
  }

  suspend() {
    if (this.needsRefresh()) throw this.refresh();
    return this;
  }
}

const useCredentials = () =>
  useMemoEq({
    guest: Config.useConfig().guestCredentials,
    req: APIConnector.use(),
    auth: reduxHook.useMappedState(Auth.selectors.authenticated),
  }, (i) =>
    i.auth ? new RegistryCredentials({ req: i.req }) : i.guest);

const Ctx = React.createContext();

// eslint-disable-next-line react/prop-types
export const Provider = ({ children }) =>
  <Ctx.Provider value={useCredentials()}>{children}</Ctx.Provider>;

export const use = () => React.useContext(Ctx);
