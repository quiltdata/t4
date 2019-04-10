import * as React from 'react';
import ExpansionPanel from '@material-ui/core/ExpansionPanel';
import ExpansionPanelDetails from '@material-ui/core/ExpansionPanelDetails';
import ExpansionPanelSummary from '@material-ui/core/ExpansionPanelSummary';
import Icon from '@material-ui/core/Icon';
import Typography from '@material-ui/core/Typography';
import { makeStyles } from '@material-ui/styles';

import ButtonIcon from 'components/ButtonIcon';


const useStyles = makeStyles({
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
});

// eslint-disable-next-line react/prop-types
export default ({ icon, heading, defaultExpanded, children, expandable = true }) => {
  const classes = useStyles();

  return (
    <ExpansionPanel
      defaultExpanded={defaultExpanded}
      expanded={expandable ? undefined : true}
    >
      <ExpansionPanelSummary
        expandIcon={expandable && <Icon>expand_more</Icon>}
        classes={{
          expanded: classes.summaryExpanded,
          root: classes.summaryRoot,
          content: classes.summaryContent,
        }}
      >
        <Typography variant="button" className={classes.heading}>
          {!!icon && <ButtonIcon>{icon}</ButtonIcon>}{heading}
        </Typography>
      </ExpansionPanelSummary>
      <ExpansionPanelDetails>{children}</ExpansionPanelDetails>
    </ExpansionPanel>
  );
};
