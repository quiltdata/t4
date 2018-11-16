/* constants for use in CSS. prefer integers over strings so we can do math */
import getMuiTheme from 'material-ui/styles/getMuiTheme';
import * as colors from '@material-ui/core/colors';
import { createMuiTheme } from '@material-ui/core/styles';
import { fade, lighten } from '@material-ui/core/styles/colorManipulator';


export const appBackgroundColor = colors.grey[50];
export const backgroundColor = 'rgb(16, 16, 16)';
export const bodyColor = colors.grey[900];
export const bodySize = '1em';
//  inspiration: https://v4-alpha.getbootstrap.com/layout/overview/#responsive-breakpoints
//  these are the bottoms of the breakpoints (min-width)
export const breaks = {
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
};
Object.freeze(breaks);
export const detailColorHex = colors.grey[700];
export const headerColor = colors.grey[900];

export const rowVSpace = '1em';

const paletteV0 = {
  primary1Color: backgroundColor,
  primary2Color: 'rgb(2, 58, 71)',
  accent1Color: colors.orange[600],
  accent2Color: colors.grey[200],
  accent3Color: colors.grey[300],
  textColor: colors.grey[800], // see also global-styles.js
  borderColor: colors.grey[400],
};

export const themeV0 = getMuiTheme({
  palette: paletteV0,
  tableRow: {
    stripeColor: fade(lighten(paletteV0.primary1Color, 0.5), 0.1),
  },
});

export const theme = createMuiTheme({
  palette: {
    primary: {
      main: colors.grey[900],
    },
    secondary: {
      main: colors.orange[600],
    },
  },
  typography: {
    useNextVariants: true,
  },
});

export const themeInverted = createMuiTheme({
  palette: {
    type: 'dark',
    primary: {
      main: colors.grey[900],
    },
    secondary: {
      main: colors.orange[600],
    },
  },
  typography: {
    useNextVariants: true,
  },
});
