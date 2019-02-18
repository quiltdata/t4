import 'aws-sdk/lib/config';
import AWS from 'aws-sdk/lib/core';
import * as R from 'ramda';
import * as React from 'react';

import * as RT from 'utils/reactTools';

import * as Credentials from './Credentials';


const Ctx = React.createContext();

const useConfig = (props) => {
  const credentials = Credentials.use();
  const ref = React.useRef(null);
  const input = { credentials, ...props };
  if (R.equals(ref.current && ref.current.input, input)) {
    return ref.current.config;
  }
  const config = new AWS.Config(input);
  ref.current = { config, input };
  return config;
};

export const Provider = RT.composeComponent('AWS.Config.Provider',
  ({ children, ...props }) => {
    const config = useConfig(props);
    return <Ctx.Provider value={config}>{children}</Ctx.Provider>;
  });

export const inject = (prop = 'awsConfig') =>
  RT.composeHOC('AWS.Config.inject', RT.consume(Ctx, prop));

export const use = () => React.useContext(Ctx);
