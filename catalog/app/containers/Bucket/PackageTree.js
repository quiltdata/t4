import * as React from 'react';

import * as RT from 'utils/reactTools';


export default RT.composeComponent('Bucket.PackageTree',
  ({ match: { params: { bucket, name, revision, path } } }) =>
    <h1>pkg tree in {bucket} for {name}@{revision}:{path}</h1>);
