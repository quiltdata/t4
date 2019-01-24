import { basename } from 'path';

import dedent from 'dedent';
import * as R from 'ramda';
import * as React from 'react';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import { withStyles } from '@material-ui/core/styles';

import ButtonIcon from 'components/ButtonIcon';
import ContentWindow from 'components/ContentWindow';
import * as AWS from 'utils/AWS';
import * as NamedRoutes from 'utils/NamedRoutes';
import { composeComponent } from 'utils/reactTools';
import { getBreadCrumbs } from 'utils/s3paths';
import withParsedQuery from 'utils/withParsedQuery';

import BreadCrumbs, { Crumb } from './BreadCrumbs';
import CodeButton from './CodeButton';


const getCrumbs = R.compose(R.intersperse(Crumb.Sep(' / ')),
  ({ bucket, path, urls }) =>
    [{ label: bucket, path: '' }, ...getBreadCrumbs(path)]
      .map(({ label, path: segPath }) =>
        Crumb.Segment({
          label,
          to: segPath === path ? undefined : urls.bucketDir(bucket, segPath),
        })));

const fileCode = ({ bucket, path }) => dedent`
  import t4
  b = Bucket("s3://${bucket}")
  # replace ./${basename(path)} to change destination file
  b.fetch("${path}", "./${basename(path)}")
`;

export default composeComponent('Bucket.File',
  withParsedQuery,
  withStyles(({ spacing: { unit } }) => ({
    topBar: {
      alignItems: 'flex-start',
      display: 'flex',
      marginBottom: 2 * unit,
      marginTop: unit,
    },
    spacer: {
      flexGrow: 1,
    },
    button: {
      color: 'inherit !important',
      marginLeft: unit,
      textDecoration: 'none !important',
    },
  })),
  ({
    match: { params: { bucket, path } },
    location: { query: { version } },
    classes,
  }) => (
    <React.Fragment>
      <div className={classes.topBar}>
        <NamedRoutes.Inject>
          {({ urls }) => (
            <BreadCrumbs items={getCrumbs({ bucket, path, urls })} />
          )}
        </NamedRoutes.Inject>
        <div className={classes.spacer} />
        <CodeButton>{fileCode({ bucket, path })}</CodeButton>
        <AWS.Signer.Inject>
          {(signer) => (
            <Button
              variant="outlined"
              href={signer.getSignedS3URL({ bucket, key: path, version })}
              className={classes.button}
            >
              <ButtonIcon position="left">arrow_downward</ButtonIcon> Download
            </Button>
          )}
        </AWS.Signer.Inject>
      </div>
      <Card>
        <CardContent>
          <ContentWindow handle={{ bucket, key: path, version }} />
        </CardContent>
      </Card>
    </React.Fragment>
  ));
