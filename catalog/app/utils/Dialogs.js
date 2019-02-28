import * as React from 'react';
import Dialog from '@material-ui/core/Dialog';

import defer from 'utils/defer';


export const use = () => {
  // open | closed | closing
  const [state, setState] = React.useState('closed');
  // { node, resolver }
  const [dialog, setDialog] = React.useState(null);

  const open = React.useCallback((fn) => {
    const { resolver, promise } = defer();
    const node = fn({ close });
    setDialog({ node, resolver });
    setState('open');
    return promise;
  }, [setDialog, setState]);

  const cleanup = React.useCallback(() => {
    if (state === 'closing') {
      setState('closed');
      setDialog(null);
    }
  }, [state, setState, setDialog]);

  const close = React.useCallback((reason) => {
    if (dialog) dialog.resolver.resolve(reason);
    setState('closing');
  }, [setState]);

  const render = () => (
    <Dialog
      open={state === 'open'}
      onClose={close}
      onExited={cleanup}
    >
      {dialog ? dialog.node : ''}
    </Dialog>
  );

  return { open, render };
};
