import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { unstable_Box as Box } from '@material-ui/core/Box';
import CircularProgress from '@material-ui/core/CircularProgress';
import Icon from '@material-ui/core/Icon';

import * as AWS from 'utils/AWS';
import { useCurrentBucketConfig } from 'utils/BucketConfig';
import { useConfig } from 'utils/Config';
import { withBoundary } from 'utils/ErrorBoundary';
import { mkSearch } from 'utils/NamedRoutes';
import * as Cache from 'utils/ResourceCache';
import * as RT from 'utils/reactTools';


const SIZES = {
  sm: { w: 256, h: 256 },
  lg: { w: 1024, h: 768 },
};

const sizeStr = (s) => `w${SIZES[s].w}h${SIZES[s].h}`;

const ThumbnailResource = Cache.createResource({
  name: 'Thumbnail',
  fetch: async ({ api, sign, handle, size }) => {
    const url = sign(handle);
    const endpoint = `${api}/thumbnail${mkSearch({ url, size: sizeStr(size) })}`;
    const r = await fetch(endpoint);
    const json = await r.json();
    const fmt = json.info.thumbnail_format.toLowerCase();
    return `data:image/${fmt};base64, ${json.thumbnail}`;
  },
  key: ({ api, handle, size }) => ({ api, handle, size }),
});

export const use = ({ handle, size }) => {
  const cfg = useConfig();
  const bucket = useCurrentBucketConfig() || {};
  const api = bucket.apiGatewayEndpoint || cfg.apiGatewayEndpoint;
  const sign = AWS.Signer.useS3Signer();
  return Cache.useData(ThumbnailResource, { api, sign, handle, size },
    { suspend: true });
};

// eslint-disable-next-line react/prop-types
const Container = ({ size, children }) => (
  <Box
    display="flex"
    alignItems="center"
    justifyContent="center"
    height={SIZES[size].h}
    bgcolor="grey.100"
    width={1}
  >
    {children}
  </Box>
);

export default RT.composeComponent('Thumbnail',
  RC.setPropTypes({
    handle: PT.object.isRequired,
    size: PT.oneOf(['sm', 'lg']),
  }),
  RC.defaultProps({
    size: 'sm',
  }),
  withBoundary((props) => (error) => {
    // eslint-disable-next-line no-console
    console.warn('Error loading thumbnail', props);
    // eslint-disable-next-line no-console
    console.error(error);
    return (
      // eslint-disable-next-line react/prop-types
      <Container size={props.size}>
        <Icon fontSize="large" title="Error loading thumbnail">warning</Icon>
      </Container>
    );
  }),
  RT.withSuspense(({ size }) =>
    <Container size={size}><CircularProgress /></Container>),
  ({ handle, size, alt = '', ...props }) => {
    const src = use({ handle, size });
    return <img src={src} alt={alt} {...props} />;
  });
