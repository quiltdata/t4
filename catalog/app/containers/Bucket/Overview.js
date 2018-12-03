import * as React from 'react';

import * as RT from 'utils/reactTools';

import Message from './Message';
import Summary from './Summary';


export default RT.composeComponent('Bucket.Overview',
  ({ match: { params: { bucket } } }) => (
    <Summary
      bucket={bucket}
      path=""
      progress
      whenEmpty={() => (
        // TODO: get started guide
        <Message headline="No overview">
          <a
            href="https://github.com/quiltdata/t4/blob/master/UserDocs.md#using-the-catalog"
          >
            Learn how to create an overview
          </a>.
        </Message>
      )}
    />
  ));
