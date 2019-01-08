import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';

import AsyncResult from 'utils/AsyncResult';
import * as RT from 'utils/reactTools';


const Ctx = React.createContext();

export const Placeholder = RT.composeComponent('Wait.Placeholder',
  RC.setPropTypes({
    fallback: PT.func.isRequired,
  }),
  ({ fallback, children }) =>
    <Ctx.Provider value={fallback}>{children}</Ctx.Provider>);

export const wait = (next) => AsyncResult.case({
  Ok: (res) => next(res),
  _: (inst) => (
    <Ctx.Consumer>
      {(fallback) => fallback(inst)}
    </Ctx.Consumer>
  ),
});
