import * as React from 'react';
import { unstable_Box as Box } from '@material-ui/core/Box';
import Button from '@material-ui/core/Button';

import FAIcon from 'components/FAIcon';
import Feature from 'components/Feature';
import Layout from 'components/Layout';
import * as urls from 'constants/urls';


const openIntercom = () => {
  if (window.Intercom) {
    window.Intercom('show');
  }
};

export default () => (
  <Layout
    dark
    pre={
      <React.Fragment>
        <Feature
          header="Collaborate in S3"
          tagline="Search, visualize, and version with the Quilt Data Catalog"
        />
        <Box
          bgcolor="common.white"
          display="flex"
          p={2}
        >
          <Box flexGrow={1} />
          <Button href={urls.slackInvite}>
            <FAIcon type="slack" />&nbsp;Join Slack
          </Button>
          <Button href={urls.t4Docs}>
            <FAIcon type="book" />&nbsp;Read Docs
          </Button>
          <Button onClick={openIntercom}>
            <FAIcon type="chatBubble" />&nbsp;Chat
          </Button>
        </Box>
      </React.Fragment>
    }
  >
  </Layout>
);
