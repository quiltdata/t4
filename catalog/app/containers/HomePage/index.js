/* HomePage */
import React from 'react';

import CTA from 'components/CallToAction';
import Feature from 'components/Feature';
import { BigSkip, Pad, UnPad } from 'components/LayoutHelpers';
import QButton from 'components/QButton';


export default class HomePage extends React.PureComponent { // eslint-disable-line react/prefer-stateless-function
  render() {
    return (
      <UnPad>
        <Feature
          header="T4 Web Catalog - Alpha Preview"
          tagline="Search, browse, and preview S3 buckets"
        />
        <CTA />
        <Pad top left right bottom>
          <h1>Documentation</h1>
          <p>Every file in T4 is indexed, versioned, and secure. T4 consists of a web catalog and a Python API.</p>
          <QButton
            href="https://github.com/quiltdata/t4/blob/master/README.md"
            label="View docs"
          />
        </Pad>
        <BigSkip />
      </UnPad>
    );
  }
}
