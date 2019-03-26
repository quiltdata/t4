import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import CardContent from '@material-ui/core/CardContent';
import CircularProgress from '@material-ui/core/CircularProgress';
import Typography from '@material-ui/core/Typography';
import { withStyles } from '@material-ui/styles';

import * as Preview from 'components/Preview';
import AsyncResult from 'utils/AsyncResult';
import * as RT from 'utils/reactTools';

import { withSignedUrl } from './utils';


const Message = RT.composeComponent('Bucket.File.FilePreview.Message',
  withStyles(() => ({
    root: {
      textAlign: 'center',
      width: '100%',
    },
  })),
  ({ classes, children }) =>
    <CardContent className={classes.root}>{children}</CardContent>);

export default RT.composeComponent('Bucket.FilePreview',
  RC.setPropTypes({
    handle: PT.object.isRequired,
  }),
  withStyles(() => ({
    root: {
      alignItems: 'center',
      display: 'flex',
      justifyContent: 'center',
    },
  })),
  ({ classes, handle }) => (
    <Card className={classes.root}>
      {Preview.load(handle, AsyncResult.case({
        Ok: AsyncResult.case({
          Init: (_, { fetch }) => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Large files are not previewed automatically
              </Typography>
              <Button variant="outlined" onClick={fetch}>Load preview</Button>
            </Message>
          ),
          Pending: () => <Message><CircularProgress /></Message>,
          Err: (_, { fetch }) => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Error loading preview
              </Typography>
              <Button variant="outlined" onClick={fetch}>Retry</Button>
            </Message>
          ),
          Ok: (data) => Preview.render(data, { className: classes.preview }),
        }),
        Err: Preview.PreviewError.case({
          // eslint-disable-next-line react/prop-types
          TooLarge: () => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Object is too large to preview in browser
              </Typography>
              {withSignedUrl(handle, (url) => (
                <Button variant="outlined" href={url}>View raw</Button>
              ))}
            </Message>
          ),
          // eslint-disable-next-line react/prop-types
          Unsupported: () => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Preview not available
              </Typography>
              {withSignedUrl(handle, (url) => (
                <Button variant="outlined" href={url}>View raw</Button>
              ))}
            </Message>
          ),
          DoesNotExist: () => (
            <Message>
              <Typography variant="body1">Object does not exist</Typography>
            </Message>
          ),
          // eslint-disable-next-line react/prop-types
          MalformedJson: ({ originalError: { message } }) => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Malformed JSON: {message}
              </Typography>
            </Message>
          ),
          Unexpected: (_, { fetch }) => (
            <Message>
              <Typography variant="body1" gutterBottom>
                Error loading preview
              </Typography>
              <Button variant="outlined" onClick={fetch}>Retry</Button>
            </Message>
          ),
        }),
        _: () => <Message><CircularProgress /></Message>,
      }))}
    </Card>
  ));
