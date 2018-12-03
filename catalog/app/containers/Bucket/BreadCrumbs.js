import PT from 'prop-types';
import * as React from 'react';
import { Link } from 'react-router-dom';
import * as RC from 'recompose';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import * as RT from 'utils/reactTools';
import tagged from 'utils/tagged';


export const Crumb = tagged([
  'Segment', // { label, to }
  'Sep', // value
]);

export default RT.composeComponent('Bucket.BreadCrumbs',
  RC.setPropTypes({
    items: PT.array.isRequired,
  }),
  withStyles(({ typography }) => ({
    root: {
      fontWeight: typography.fontWeightRegular,
    },
  })),
  ({ classes, items }) => (
    <Typography variant="h6" className={classes.root}>
      {items.map(Crumb.case({
        // eslint-disable-next-line react/prop-types
        Segment: ({ label, to }) =>
          to
            ? <Link key={label} to={to}>{label}</Link>
            : <span key={label}>{label}</span>,
        Sep: (s, i) => <span key={`__sep${i}`}>{s}</span>,
      }))}
    </Typography>
  ));