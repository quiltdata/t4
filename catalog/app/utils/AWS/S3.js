import S3 from 'aws-sdk/clients/s3';
import * as React from 'react';

import * as RT from 'utils/reactTools';
import useMemoEq from 'utils/useMemoEq';

import * as Config from './Config';
import * as Credentials from './Credentials';


const Ctx = React.createContext();

export const Provider = RT.composeComponent('AWS.S3.Provider',
  ({ children, ...props }) =>
    <Ctx.Provider value={props}>{children}</Ctx.Provider>);

export const use = () => {
  const config = Config.use();
  Credentials.use().suspend();
  const props = React.useContext(Ctx);
  // TODO: use cache?
  return useMemoEq({ ...config, ...props }, (cfg) => new S3(cfg));
};

export const inject = (prop = 's3') =>
  RT.composeHOC('AWS.S3.inject', (Component) => (props) => {
    const s3 = use();
    return <Component {...{ [prop]: s3, ...props }} />;
  });

export const Inject = ({ children }) => children(use());
