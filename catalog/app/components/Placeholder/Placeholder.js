import * as React from 'react';
import { unstable_Box as Box } from '@material-ui/core/Box';
import CircularProgress from '@material-ui/core/CircularProgress';

import Delay from 'utils/Delay';


export default () => (
  <Box
    alignItems="center"
    display="flex"
    justifyContent="center"
    minHeight="100vh"
  >
    <Delay>{() => <CircularProgress size={120} />}</Delay>
  </Box>
);
