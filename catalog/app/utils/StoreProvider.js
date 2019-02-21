import PT from 'prop-types';
import React from 'react';
import { Provider as ReduxProvider } from 'react-redux';
import { setPropTypes } from 'recompose';
import { StoreContext } from 'redux-react-hook';

import { composeComponent } from 'utils/reactTools';


export default composeComponent('StoreProvider',
  setPropTypes({
    store: PT.object.isRequired,
  }),
  ({ store, children }) => (
    <ReduxProvider store={store}>
      <StoreContext.Provider value={store}>
        {children}
      </StoreContext.Provider>
    </ReduxProvider>
  ));
