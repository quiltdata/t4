import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import Button from '@material-ui/core/Button';
import Popover from '@material-ui/core/Popover';
import { withStyles } from '@material-ui/core/styles';

import ButtonIcon from 'components/ButtonIcon';
import * as RT from 'utils/reactTools';


export default RT.composeComponent('Bucket.CodeButton',
  RC.setPropTypes({
    children: PT.node.isRequired,
  }),
  RC.withStateHandlers({
    anchor: null,
    opened: false,
  }, {
    setAnchor: () => (anchor) => ({ anchor }),
    open: () => () => ({ opened: true }),
    close: () => () => ({ opened: false }),
  }),
  withStyles(({ spacing: { unit } }) => ({
    paper: {
      padding: 2 * unit,
    },
    code: {
      background: 'none',
      border: 'none',
      margin: 0,
      padding: 0,
    },
  })),
  ({
    classes,
    children,
    anchor,
    setAnchor,
    opened,
    open,
    close,
  }) => (
    <React.Fragment>
      <Button
        variant="outlined"
        onClick={open}
        buttonRef={setAnchor}
      >
        <ButtonIcon position="left">code</ButtonIcon> Show&nbsp;code
      </Button>
      <Popover
        open={opened && !!anchor}
        anchorEl={anchor}
        onClose={close}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
        transformOrigin={{ vertical: 'top', horizontal: 'center' }}
        classes={{ paper: classes.paper }}
      >
        <pre className={classes.code}>{children}</pre>
      </Popover>
    </React.Fragment>
  ));
