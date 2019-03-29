import * as React from 'react';
import Button from '@material-ui/core/Button';
import Card from '@material-ui/core/Card';
import { makeStyles } from '@material-ui/styles';

import ButtonIcon from 'components/ButtonIcon';


const useStyles = makeStyles((t) => ({
  card: {
    marginBottom: t.spacing.unit * 2,
  },
  code: {
    fontFamily: t.typography.monospace.fontFamily,
    fontSize: t.typography.body2.fontSize,
    overflow: 'auto',
    padding: t.spacing.unit * 2,
    whiteSpace: 'pre',
  },
}));

export const use = (code) => {
  const classes = useStyles();
  const [visible, setVisible] = React.useState(true);
  const toggle = React.useCallback(() => setVisible((v) => !v), []);

  const card = visible && (
    <Card className={classes.card}>
      <div className={classes.code}>{code}</div>
    </Card>
  );

  const btn = (
    <Button variant="outlined" onClick={toggle}>
      <ButtonIcon position="left">code</ButtonIcon>
      {' '}{visible ? 'Hide' : 'Show'}&nbsp;code
    </Button>
  );

  return { card, btn };
};
