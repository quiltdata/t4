import * as React from 'react';

import AsyncResult from 'utils/AsyncResult';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import { useRoute } from 'utils/router';


export const useBucketConfigs = () => {
  const { federations } = Config.use();
  return React.useMemo(
    () => federations.reduce((acc, f) => ({ ...acc, [f.name]: f }), {}),
    [federations],
  );
};

export const useCurrentBucket = () => {
  const { paths } = NamedRoutes.use();
  const { match } = useRoute(paths.bucketRoot);
  return match && match.params.bucket;
};

export const useCurrentBucketConfig = () => {
  const bucket = useCurrentBucket();
  const buckets = useBucketConfigs();
  return bucket && (buckets[bucket] || { name: bucket });
};

// compatibility
export const WithCurrentBucket = ({ children }) =>
  children(useCurrentBucket());

export const WithCurrentBucketConfig = ({ children }) =>
  children(AsyncResult.Ok(useCurrentBucketConfig()));
