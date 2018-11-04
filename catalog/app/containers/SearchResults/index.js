import { Card, CardHeader, CardText } from 'material-ui/Card';
import * as colors from 'material-ui/styles/colors';
import PropTypes from 'prop-types';
import React, { Fragment } from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import { lifecycle, setPropTypes/* , compose */ } from 'recompose';
import { FormattedMessage } from 'react-intl';
import { createStructuredSelector } from 'reselect';
import styled from 'styled-components';

import apiStatus from 'constants/api';
import Error from 'components/Error';
import Help from 'components/Help';
import Layout from 'components/Layout';
import Tag from 'components/Tag';
import Working from 'components/Working';
import { ES } from 'utils/AWS';
import { setSearchText, selectSearchText } from 'utils/SearchProvider';
import { composeComponent } from 'utils/reactTools';
import { injectReducer } from 'utils/ReducerInjector';
import { injectSaga } from 'utils/SagaInjector';
import { readableBytes } from 'utils/string';
import withParsedQuery from 'utils/withParsedQuery';

import { getSearch } from './actions';
import { REDUX_KEY } from './constants';
import messages from './messages';
import reducer from './reducer';
import saga from './saga';
import { selectSearch } from './selectors';


const Heading = styled.h1`
  font-size: 1.5em;
  font-weight: 400;
  margin: 0;
`;

const SectionHeading = styled.h2`
  font-size: 18px;
  font-weight: 400;
  margin-bottom: 0;
  margin-top: 24px;

  ${Heading} + & {
    margin-top: 12px;
  }
`;

const Text = styled.pre`
  background: ${colors.grey50};
  border-color: ${colors.grey400};
  opacity: .7;
`;

const HitCard = styled(Card)`
  & + & {
    margin-top: 16px;
  }
`;

const Meta = styled.pre`
  background: ${colors.lightBlue50};
  border-color: ${colors.lightBlue400};
  opacity: .7;
`;

const Footer = styled.div`
  color: ${colors.grey500};
  margin-top: 1.5em;
`;

const Versions = styled.ul`
  list-style: none;
  padding-left: 0;
`;

const VersionContainer = styled.li`
  opacity: .7;
`;

const VersionID = styled.code`
`;

const VersionTS = styled.span`
  font-weight: 400;
`;

const Version = composeComponent('SearchResults.Version',
  setPropTypes({
    id: PropTypes.string.isRequired,
    ts: PropTypes.instanceOf(Date).isRequired,
    latest: PropTypes.bool,
  }),
  ({ id, ts, latest = false }) => (
    <VersionContainer>
      <VersionID>{id}</VersionID>
      <span> from </span>
      <VersionTS>{ts.toLocaleString()}</VersionTS>
      {latest && <Tag>latest</Tag>}
    </VersionContainer>
  ));

const Hit = composeComponent('SearchResults.Hit',
  ({
    path,
    timestamp,
    size,
    text,
    // eslint-disable-next-line camelcase
    user_meta: meta,
    versions,
  }) => (
    <HitCard>
      <CardText style={{ paddingBottom: 0 }}>
        <Heading>
          <Link to={`/browse/${path}`}>{path}</Link>
        </Heading>
        {!!text && <Text>{text}</Text>}
        {!!meta && (
          <Fragment>
            <SectionHeading>Metadata</SectionHeading>
            <Meta>{JSON.stringify(meta, null, 2)}</Meta>
          </Fragment>
        )}
        {versions.length && (
          <Fragment>
            <SectionHeading>Versions</SectionHeading>
            <Versions>
              {versions.map(({ id, timestamp: ts }, idx) => (
                <Version
                  key={id}
                  latest={idx === 0}
                  id={id}
                  ts={ts}
                />
              ))}
            </Versions>
          </Fragment>
        )}
        <Footer>
          Updated {timestamp.toLocaleString()}
          &nbsp;&nbsp;&nbsp;&nbsp;
          {readableBytes(size)}
        </Footer>
      </CardText>
    </HitCard>
  ));

const NothingFound = () => (
  <Card>
    <CardHeader
      title="Nothing found"
      subtitle="We have not found anything matching your query"
    />
  </Card>
);

export default composeComponent('SearchResults',
  ES.inject(),
  injectReducer(REDUX_KEY, reducer),
  injectSaga(REDUX_KEY, saga),
  withParsedQuery,
  connect(createStructuredSelector({
    search: selectSearch,
    searchText: selectSearchText,
  })),
  setPropTypes({
    dispatch: PropTypes.func.isRequired,
    location: PropTypes.shape({
      query: PropTypes.object.isRequired,
    }).isRequired,
    search: PropTypes.object.isRequired,
    searchText: PropTypes.string.isRequired,
  }),
  lifecycle({
    componentWillMount() {
      const {
        location: { query: { q } },
        searchText,
        dispatch,
      } = this.props;
      if (q !== searchText) dispatch(setSearchText(q));
      dispatch(getSearch(q));
    },
    componentWillReceiveProps({ dispatch, searchText, location: { query: { q } } }) {
      const oldQ = this.props.location.query.q;
      if (q !== oldQ) {
        dispatch(getSearch(q));
        if (q !== searchText) dispatch(setSearchText(q));
      }
    },
    componentWillUnmount() {
      this.props.dispatch(setSearchText(''));
    },
  }),
  ({ search }) => (
    <Layout>
      {(({ error, status, response }) => {
        // eslint-disable-next-line default-case
        switch (status) {
          case undefined:
          case apiStatus.WAITING:
            return <Working><FormattedMessage {...messages.header} /></Working>;
          case apiStatus.ERROR:
            return <Error {...error} />;
        }
        return (
          <div>
            <h1><FormattedMessage {...messages.header} /></h1>
            {response.length
              ? response.map((result) => <Hit key={result.path} {...result} />)
              : <NothingFound />
            }
            <br />
            <Help to="/browse/">Browse registry</Help>
            <br />
            {/*
            {response.length === 0 ? null : (
              <Fragment>
                <h1>New packages</h1>
                <Gallery />
              </Fragment>
            )}
            */}
            <br />
          </div>
        );
      })(search)}
    </Layout>
  ));
