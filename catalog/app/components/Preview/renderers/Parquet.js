import * as React from 'react';


// TODO
export default ({ preview }, props) =>
  // eslint-disable-next-line react/no-danger
  <div dangerouslySetInnerHTML={{ __html: preview }} {...props} />;
