import { createSelector } from 'reselect';

import { get, toJS } from 'utils/immutableTools';

import { REDUX_KEY } from './constants';


export default createSelector(get(REDUX_KEY), toJS());
