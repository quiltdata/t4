import * as reduxHook from 'redux-react-hook';

import * as Auth from 'containers/Auth';
import * as APIConnector from 'utils/APIConnector';
import * as Config from 'utils/Config';
import * as Cache from 'utils/ResourceCache';


// TODO: refresh

const CredentialsResource = Cache.createResource({
  name: 'AWS.Credentials',
  fetch: ({ req }) => req({ endpoint: '/auth/get_credentials' }),
  key: () => null,
});

export const use = () => {
  const cfg = Config.useConfig();
  const req = APIConnector.use();
  const cache = Cache.use();
  const authenticated = reduxHook.useMappedState(Auth.selectors.authenticated);
  return authenticated
    ? cache(CredentialsResource, { req })
    : cfg.guestCredentials;
};
