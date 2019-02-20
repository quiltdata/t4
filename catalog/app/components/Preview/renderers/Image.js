import cx from 'classnames';
import * as React from 'react';
import { withStyles } from '@material-ui/core/styles';

import * as RT from 'utils/reactTools';


const Image = RT.composeComponent('Preview.renderers.Image',
  withStyles(() => ({
    root: {
      display: 'block',
      maxWidth: '100%',
    },
  })),
  ({ classes, className, ...props }) =>
    <img className={cx(className, classes.root)} alt="" {...props} />);

export default ({ url }, props) => <Image src={url} {...props} />;
