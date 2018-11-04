import {
  ConnectedRouter,
  connectRouter,
} from 'connected-react-router/immutable';

import { composeComponent } from 'utils/reactTools';
import { injectReducerFactory } from 'utils/ReducerInjector';


export const REDUX_KEY = 'router';

export default composeComponent('RouterProvider',
  injectReducerFactory(REDUX_KEY, ({ history }) => connectRouter(history)),
  ConnectedRouter);
