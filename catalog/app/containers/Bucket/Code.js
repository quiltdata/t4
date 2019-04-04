import * as React from 'react';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import Icon from '@material-ui/core/Icon';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/styles';

import ButtonIcon from 'components/ButtonIcon';


const useStyles = makeStyles((t) => ({
  root: {
    marginBottom: t.spacing.unit * 2,
  },
  code: {
    fontFamily: t.typography.monospace.fontFamily,
    fontSize: t.typography.body2.fontSize,
    overflow: 'auto',
    whiteSpace: 'pre',
  },
  summaryExpanded: {
  },
  summaryRoot: {
    '&$summaryExpanded': {
      minHeight: 48,
    },
  },
  summaryContent: {
    '&$summaryExpanded': {
      margin: [[12, 0]],
    },
  },
  heading: {
    display: 'flex',
  },
}));

// eslint-disable-next-line react/prop-types
export default ({ children }) => {
  const classes = useStyles();

  return (
    <ExpansionPanel className={classes.root} defaultExpanded>
      <ExpansionPanelSummary
        expandIcon={<Icon>expand_more</Icon>}
        classes={{
          expanded: classes.summaryExpanded,
          root: classes.summaryRoot,
          content: classes.summaryContent,
        }}
      >
        <Typography variant="button" className={classes.heading}>
          <ButtonIcon>code</ButtonIcon>Code
        </Typography>
      </ExpansionPanelSummary>
      <ExpansionPanelDetails>
        <div className={classes.code}>{children}</div>
      </ExpansionPanelDetails>
    </ExpansionPanel>
  );
};
