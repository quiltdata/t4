import * as React from 'react';
import { Link } from 'react-router-dom';

import * as NamedRoutes from 'utils/NamedRoutes';
import * as RT from 'utils/reactTools';

import Message from './Message';
import Summary from './Summary';


const DOC_LINK =
  'https://github.com/quiltdata/t4/blob/master/UserDocs.md#using-the-catalog';
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
          Currently there`s no overview in this bucket
          &mdash; <a href={DOC_LINK}>learn how to create one</a>.
          <br />
          Also, check out
          our <Link to={urls.bucketRoot(EXAMPLE_BUCKET)}>example bucket</Link> to
          see what T4 is capable of.
        </Message>
      )}
    />
  ));
