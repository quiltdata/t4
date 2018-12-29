import * as React from 'react';

import * as NamedRoutes from 'utils/NamedRoutes';
import Link from 'utils/StyledLink';
import * as RT from 'utils/reactTools';

import Message from './Message';
import Summary from './Summary';


const EXAMPLE_BUCKET = 'quilt-example';

export default RT.composeComponent('Bucket.Overview',
  NamedRoutes.inject(),
  ({ urls, match: { params: { bucket } } }) => (
    <Summary
      bucket={bucket}
      path=""
      progress
      whenEmpty={() => (
        <Message headline="Getting Started">
          Welcome to the Quilt T4 catalog for the <strong>{bucket}</strong> bucket.
          <br />
          For help getting started with T4 check
          out <Link to={urls.bucketRoot(EXAMPLE_BUCKET)}>the demo bucket</Link>.
          <br />
          To overwrite this landing page with your own, create a
          new <strong>README.md</strong> at the top level of this bucket.
        </Message>
      )}
    />
  ));
