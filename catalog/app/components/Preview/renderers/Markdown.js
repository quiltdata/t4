import cx from 'classnames';
import * as React from 'react';
import { withStyles } from '@material-ui/core/styles';

import { Container } from 'components/Markdown';
import * as RT from 'utils/reactTools';


const Markdown = RT.composeComponent('Preview.renderers.Markdown',
  withStyles((t) => ({
    root: {
      padding: t.spacing.unit * 1.5,
    },
  })),
  ({ classes, className, ...props }) =>
    <Container className={cx(className, classes.root)} {...props} />);

export default ({ rendered }, props) =>
  <Markdown {...props}>{rendered}</Markdown>;
