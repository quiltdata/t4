import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/core/styles';

import Link from 'utils/StyledLink';
import * as RT from 'utils/reactTools';
import tagged from 'utils/tagged';


export const Crumb = tagged([
  'Segment', // { label, to }
  'Sep', // value
]);

export const Segment = RT.composeComponent('Bucket.BreadCrumbs.Segment',
  RC.setPropTypes({
    label: PT.string.isRequired,
    to: PT.string,
  }),
  withStyles(() => ({
    root: {
      whiteSpace: 'nowrap',
    },
  })),
  ({ classes, label, to }) => {
    const Component = to ? Link : 'span';
    return <Component to={to} className={classes.root}>{label}</Component>;
  });

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
        Segment: (s, i) => <Segment key={`${i}:${s.label}`} {...s} />,
        Sep: (s, i) => <span key={`__sep${i}`}>{s}</span>,
      }))}
    </Typography>
  ));
