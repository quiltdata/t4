/* CallToAction */
import React from 'react';
import { Col, Row } from 'react-bootstrap';
import FlatButton from 'material-ui/FlatButton';
import styled from 'styled-components';
import { slackInvite, t4Docs } from 'constants/urls';

import FAIcon from 'components/FAIcon';

const Styler = styled(Row)`
  color: white;
  padding: 16px;
  text-align: right;
`;

function openIntercom() {
  // eslint-disable-next-line no-undef
  if (Intercom) {
    // eslint-disable-next-line no-undef
    Intercom('show');
  }
}

// terrible hack to avoid extremely funky layout bugs with material-ui
// which returns a different compnent type when href is given
// TODO fix this
const go = (dest) => () => { window.location = dest; };

function CallToAction() {
  return (
    <Styler>
      <Col xs={12}>
        <FlatButton
          label={<span><FAIcon type="slack">check</FAIcon> Join Slack</span>}
          onClick={go(slackInvite)}
        />
        <FlatButton
          label={<span><FAIcon type="book">check</FAIcon> Read Docs</span>}
          onClick={go(t4Docs)}
        />
        <FlatButton
          label={<span><FAIcon type="chatBubble">check</FAIcon> Chat</span>}
          onClick={openIntercom}
        />
      </Col>
    </Styler>
  );
}

export default CallToAction;
