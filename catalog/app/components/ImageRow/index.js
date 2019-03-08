import PropTypes from 'prop-types';
import React from 'react';
import { Col, Row } from 'react-bootstrap';
import styled from 'styled-components';

import { backgroundColor as bgc } from 'constants/style';

const Back = styled.div`
  background-color: ${(props) => props.backgroundColor};
  background-image: url(${(props) => props.src});
  background-position: ${(props) => props.hero ? 'center' : 'default'};
  background-repeat: no-repeat;
  background-size: ${(props) => props.hero ? 'contain' : 'cover'};
  height: ${(props) => props.height};
  padding-top: ${(props) => props.paddingTop};
`;

/* Rows with images as their background */
// TODO better to just spread props to Back than pipe by hand
// eslint-disable-next-line object-curly-newline
const ImageRow = ({ backgroundColor=bgc, children, height, src, hero=false }) => (
    <Row>
        <Back backgroundColor={backgroundColor} height={height} hero={hero} src={src}>
          { React.Children.toArray(children) }
        </Back>
    </Row>
);

ImageRow.propTypes = {
  backgroundColor: PropTypes.string,
  children: PropTypes.any,
  height: PropTypes.string,
  hero: PropTypes.bool,
  src: PropTypes.string.isRequired,
};

export default ImageRow;
