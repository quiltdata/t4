import cx from 'classnames';
import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/styles';

import 'katex/dist/katex.css';

import * as RT from 'utils/reactTools';


const Notebook = RT.composeComponent('Preview.renderers.Notebook',
  RC.setPropTypes({
    children: PT.string,
    className: PT.string,
  }),
  withStyles(({ spacing: { unit } }) => ({
    root: {
      padding: unit,
      width: '100%',
    },
  })),
  ({ classes, children, className, ...props } = {}) => (
    <div
      className={cx(className, classes.root, 'ipynb-preview')}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: children }}
      {...props}
    />
  ));

export default ({ preview }, props) =>
  <Notebook {...props}>{preview}</Notebook>;
