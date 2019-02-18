const MAX_TRIES = 30;

/* istanbul ignore next */
const isAutofilled = (el) => {
  try {
    return el.matches(':autofill');
  } catch (e) {
    try {
      return el.matches(':-webkit-autofill');
    } catch (ee) {
      return false;
    }
  }
};

export default (el) => {
  if (!el) return;
  const input = el.getInputNode();
  if (!input) return;
  let tries = 0;
  // workaround for chrome autofill issue
  // see https://github.com/mui-org/material-ui/issues/718
  // and https://stackoverflow.com/questions/35049555/chrome-autofill-autocomplete-no-value-for-password
  const interval = setInterval(() => {
    const filled = isAutofilled(input);
    if (filled) {
      if (!el.state.hasValue) el.setState({ hasValue: true });
      clearInterval(interval);
    }
    tries += 1;
    if (tries > MAX_TRIES) clearInterval(interval);
  }, 100);
};
