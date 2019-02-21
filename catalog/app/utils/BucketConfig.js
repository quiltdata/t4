import AsyncResult from 'utils/AsyncResult';
import * as Config from 'utils/Config';
import * as NamedRoutes from 'utils/NamedRoutes';
import { useRoute } from 'utils/router';


export const useBucketConfigs = ({ suggestedOnly = false } = {}) => {
  const { suggestedBuckets, federations } = Config.use();
  return suggestedOnly
    ? federations.filter(({ name }) => suggestedBuckets.includes(name))
    : federations;
};

export const useCurrentBucket = () => {
  const { paths } = NamedRoutes.use();
  const { match } = useRoute(paths.bucketRoot);
  return match && match.params.bucket;
};

export const useCurrentBucketConfig = () => {
  const bucket = useCurrentBucket();
  const buckets = useBucketConfigs();

  return bucket
    && (buckets.find(({ name }) => name === bucket) || { name: bucket });
};

// compatibility
export const WithBucketConfigs = ({ children, suggestedOnly }) =>
  children(AsyncResult.Ok(useBucketConfigs({ suggestedOnly })));

export const WithCurrentBucket = ({ children }) =>
  children(useCurrentBucket());

export const WithCurrentBucketConfig = ({ children }) =>
  children(AsyncResult.Ok(useCurrentBucketConfig()));
