import { basename } from 'path';

import { Card, CardText } from 'material-ui/Card';
import RaisedButton from 'material-ui/RaisedButton';
import PT from 'prop-types';
import * as React from 'react';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  lifecycle,
  withProps,
  withHandlers,
  setPropTypes,
} from 'recompose';
import styled from 'styled-components';

import MIcon from 'components/MIcon';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { S3, Signer } from 'utils/AWS';
import AsyncResult from 'utils/AsyncResult';
import { injectReducer } from 'utils/ReducerInjector';
import {
  getBreadCrumbs,
  isDir,
} from 'utils/s3paths';
import { injectSaga } from 'utils/SagaInjector';
import { composeComponent, extractProp } from 'utils/reactTools';

import ContentWindow from './ContentWindow';
import Listing from './Listing';
import Summary, { SummaryItem } from './Summary';
import { REDUX_KEY } from './constants';
import saga from './saga';
import selector from './selectors';
import reducer, { Action } from './reducer';


const BreadCrumbs = composeComponent('Browser.BreadCrumbs',
  setPropTypes({
    path: PT.string.isRequired,
    root: PT.string.isRequired,
  }),
  ({ path, root }) => (
    <h3 style={{ fontSize: 18, margin: 0 }}>
      {path
        ? <Link to="/browse/">{root}</Link>
        : root
      }
      {getBreadCrumbs(path).map((b) => (
        <span key={b}>
          <span> / </span>
          {b === path
            ? basename(b)
            : <Link to={`/browse/${b}`}>{basename(b)}</Link>
          }
        </span>
      ))}
    </h3>
  ));

const ErrorDisplay = composeComponent('Browser.ErrorDisplay',
  setPropTypes({
    retry: PT.func,
    children: PT.node,
  }),
  ({ retry, children }) => (
    <h3>
      <MIcon>warning</MIcon>
      {children || 'Something went wrong'}
      {!!retry && <RaisedButton label="Retry" onClick={retry} />}
    </h3>
  ));

const FileDisplay = composeComponent('Browser.FileDisplay',
  setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
  }),
  ({ bucket, path }) => (
    // TODO: meta
    // TODO: download
    <Card style={{ marginTop: 16 }}>
      <CardText>
        <ContentWindow handle={{ bucket, key: path }} />
      </CardText>
    </Card>
  ));

const Placeholder = () => <Spinner style={{ fontSize: '3em' }} />;

const DirectoryDisplay = composeComponent('Browser.DirectoryDisplay',
  setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string.isRequired,
  }),
  S3.inject(),
  injectSaga(REDUX_KEY, saga),
  injectReducer(REDUX_KEY, reducer),
  connect(selector),
  withHandlers({
    getData: ({ dispatch, path }) => () => {
      dispatch(Action.Get({ path }));
    },
  }),
  lifecycle({
    componentWillMount() {
      this.props.getData();
    },
    componentWillReceiveProps(nextProps) {
      if (this.props.path !== nextProps.path) {
        nextProps.getData();
      }
    },
  }),
  extractProp('state', AsyncResult.case({
    _: () => <Placeholder />,
    // eslint-disable-next-line react/prop-types
    Ok: ({ files, directories, readme, summary }, { path }) => (
      <React.Fragment>
        <Listing
          prefix={path}
          directories={directories}
          files={files}
        />
        {readme && (
          <SummaryItem
            title={basename(readme.key)}
            handle={readme}
          />
        )}
        {summary && (
          <Summary handle={summary} />
        )}
      </React.Fragment>
    ),
    Err: (err, { getData }) => (
      <ErrorDisplay retry={getData} />
    ),
  })));

const TopBar = styled.div`
  align-items: baseline;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  margin-bottom: 16px;
  margin-top: 4px;
`;

export default composeComponent('Browser',
  Signer.inject(),
  withProps(({ match: { params: { path } } }) => ({
    bucket: config.aws.s3Bucket,
    path,
  })),
  ({ bucket, path, signer }) => (
    <div>
      <TopBar>
        <BreadCrumbs path={path} root={bucket} />
        {!isDir(path) && (
          <RaisedButton
            href={signer.getSignedS3URL({ bucket, key: path })}
            label="Download file"
          />
        )}
      </TopBar>

      {isDir(path)
        ? <DirectoryDisplay bucket={bucket} path={path} />
        : <FileDisplay bucket={bucket} path={path} />
      }
    </div>
  ));
