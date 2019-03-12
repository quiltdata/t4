import cx from 'classnames';
import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/styles';

import * as RT from 'utils/reactTools';


const Parquet = RT.composeComponent('Preview.renderers.Parquet',
  RC.setPropTypes({
    children: PT.string,
    className: PT.string,
  }),
  withStyles(({ palette, spacing: { unit } }) => ({
    root: {
      overflow: 'auto',
      padding: unit,
      width: '100%',

      '& table.dataframe': {
        border: 'none',
        width: 'auto',

        '& tr:nth-child(even)': {
          backgroundColor: palette.grey[100],
        },

        '& th, & td': {
          border: 'none',
          fontSize: 'small',
        },

        '& td': {
          whiteSpace: 'nowrap',
        },
      },
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
