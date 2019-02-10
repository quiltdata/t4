import cx from 'classnames';
import * as React from 'react';


export default ({ preview }, { className, ...props } = {}) => (
  <div
    className={cx(className, 'ipynb-preview')}
    // eslint-disable-next-line react/no-danger
    dangerouslySetInnerHTML={{ __html: preview }}
    {...props}
  />
);
