import * as Config from 'utils/Config';


// saga and selectors for working with aws credentials
// hook into auth states / actions
// -- keep creds in storage
// fetch on login
// then refresh

export const use = () => {
  const cfg = Config.useConfig();
  return cfg.guestCredentials;
};
