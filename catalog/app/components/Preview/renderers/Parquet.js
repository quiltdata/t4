import cx from 'classnames';
import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/core/styles';

import * as RT from 'utils/reactTools';


const Parquet = RT.composeComponent('Preview.renderers.Parquet',
  RC.setPropTypes({
    children: PT.string,
    className: PT.string,
  }),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      overflow: 'auto',
      padding: unit,
      width: '100%',
    },
  })),
  ({ classes, children, className, ...props } = {}) => (
    <div
      className={cx(className, classes.root)}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: children }}
      {...props}
    />
  ));

export default ({ preview }, props) =>
  <Parquet {...props}>{preview}</Parquet>;
