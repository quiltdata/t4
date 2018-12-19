import { parse } from 'querystring';

import PT from 'prop-types';
import { setPropTypes, withProps } from 'recompose';

import { composeHOC } from 'utils/reactTools';


export default composeHOC('withParsedQuery',
  setPropTypes({
    location: PT.shape({
      search: PT.string.isRequired,
    }).isRequired,
  }),
  withProps(({ location }) => ({
    location: { ...location, query: parse(location.search.replace(/^\?/, '')) },
  })));
