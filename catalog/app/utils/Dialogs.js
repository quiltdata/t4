import * as React from 'react';
import Dialog from '@material-ui/core/Dialog';

import defer from 'utils/defer';


export const use = () => {
  // open | closed | closing
  const [state, setState] = React.useState('closed');
  // { render, resolver }
  const [dialog, setDialog] = React.useState(null);

  const open = React.useCallback((render) => {
    const { resolver, promise } = defer();
    setDialog({ render, resolver });
    setState('open');
    return promise;
  }, [setDialog, setState]);

  const close = React.useCallback((reason) => {
    if (dialog) dialog.resolver.resolve(reason);
    setState('closing');
  }, [setState, dialog]);

  const cleanup = React.useCallback(() => {
    if (state === 'closing') {
      setState('closed');
      setDialog(null);
    }
  }, [state, setState, setDialog]);

  const render = () => (
    <Dialog
      open={state === 'open'}
      onClose={close}
      onExited={cleanup}
    >
      {dialog ? dialog.render({ close }) : ''}
    </Dialog>
  );

  return { open, render };
};
