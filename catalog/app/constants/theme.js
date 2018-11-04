import getMuiTheme from 'material-ui/styles/getMuiTheme';
import { fade, lighten } from 'material-ui/utils/colorManipulator';

import { palette } from 'constants/style';


export default getMuiTheme({
  palette,
  tableRow: {
    stripeColor: fade(lighten(palette.primary1Color, 0.5), 0.1),
  },
});
