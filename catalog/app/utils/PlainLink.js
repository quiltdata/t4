import cx from 'classnames';
import * as React from 'react';
import { Link } from 'react-router-dom';
import { withStyles } from '@material-ui/core/styles';

import * as RT from 'utils/reactTools';


const reset = { color: 'inherit', textDecoration: 'none' };

export default RT.composeComponent('PlainLink',
  withStyles(() => ({
    root: {
      ...reset,
      '&:active, &:visited, &:focus, &:hover': reset,
    },
  })),
  ({ className, classes, ...props }) => (
    <Link className={cx(className, classes.root)} {...props} />
  ));
