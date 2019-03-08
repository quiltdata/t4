import * as React from 'react';
import { Grid } from 'react-bootstrap';

import CTA from 'components/CallToAction';
import Feature from 'components/Feature';
import Layout from 'components/Layout';
import { BigSkip, Pad, UnPad } from 'components/LayoutHelpers';
import QButton from 'components/QButton';
import { composeComponent } from 'utils/reactTools';


export default composeComponent('HomePage',
  () => (
    <Layout>
      <UnPad>
        <Grid fluid>
          <Feature
            header="Collaborate in S3"
            tagline="Search, visualize, and version with the Quilt Data Catalog"
          />
          <CTA />
        </Grid>
      </UnPad>
    </Layout>
  ));
