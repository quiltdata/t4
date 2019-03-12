import cx from 'classnames';
import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/styles';

import * as RT from 'utils/reactTools';


const Text = RT.composeComponent('Preview.renderers.Text',
  RC.setPropTypes({
    className: PT.string,
    children: PT.string,
  }),
  withStyles((t) => ({
    root: {
      fontFamily: t.typography.monospace.fontFamily,
      overflow: 'auto',
      padding: t.spacing.unit * 1.5,
      whiteSpace: 'pre',
    },
  })),
  ({ classes, className, children, ...props }) => (
    <div
      className={cx(className, classes.root)}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: children }}
      {...props}
    />
  ));

export default ({ highlighted }, props) =>
  <Text {...props}>{highlighted}</Text>;
