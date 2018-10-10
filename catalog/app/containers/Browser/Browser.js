import { basename } from 'path';

import invoke from 'lodash/fp/invoke';
import RaisedButton from 'material-ui/RaisedButton';
import PT from 'prop-types';
import * as React from 'react';
import Modal from 'react-modal';
import { connect } from 'react-redux';
import { Link } from 'react-router-dom';
import {
  lifecycle,
  withProps,
  withHandlers,
  withStateHandlers,
  setPropTypes,
} from 'recompose';

import MIcon from 'components/MIcon';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { S3 } from 'utils/AWS';
import { composeComponent } from 'utils/reactTools';
import { injectReducer } from 'utils/ReducerInjector';
import {
  up,
  splitPath,
  withoutPrefix,
} from 'utils/s3paths';
import { injectSaga } from 'utils/SagaInjector';

import ContentWindow from './ContentWindow';
import Listing from './Listing';
import Summary, { SummaryItem } from './Summary';
import { get } from './actions';
import { REDUX_KEY, EXPIRATION } from './constants';
import saga from './saga';
import selector from './selectors';
import reducer from './reducer';


const Preview = composeComponent('Browser.Preview',
  setPropTypes({
    bucket: PT.string.isRequired,
    path: PT.string,
    expiration: PT.number,
    hide: PT.func.isRequired,
  }),
  ({ bucket, path, expiration, hide }) => (
    <Modal
      isOpen={!!path}
      onRequestClose={hide}
    >
      {path && (
        <ContentWindow
          bucket={bucket}
          path={path}
          expiration={expiration}
        />
      )}
    </Modal>
  ));

const getBreadCrumbs = (prefix) =>
  prefix ? [...getBreadCrumbs(up(prefix)), prefix] : [];

const BreadCrumbs = composeComponent('Browser.BreadCrumbs',
  setPropTypes({
    prefix: PT.string.isRequired,
    root: PT.string.isRequired,
  }),
  ({ prefix, root }) => (
    <h3>
      {prefix
        ? <Link to="/browse/">{root}</Link>
        : root
      }
      {getBreadCrumbs(prefix).map((b) => (
        <span key={b}>
          <span> / </span>
          {b === prefix
            ? basename(b)
            : <Link to={`/browse/${b}`}>{basename(b)}</Link>
          }
        </span>
      ))}
    </h3>
  ));


export default composeComponent('Browser',
  withProps({
    bucket: config.aws.s3Bucket,
    expiration: EXPIRATION,
  }),
  S3.inject(),
  injectSaga(REDUX_KEY, saga),
  injectReducer(REDUX_KEY, reducer),
  connect(selector),
  withStateHandlers({
    preview: null,
  }, {
    showPreview: () => (path) => ({ preview: path }),
    hidePreview: () => () => ({ preview: null }),
  }),
  withProps(({ match: { params: { path } } }) => ({
    path,
    ...splitPath(path),
  })),
  withHandlers({
    getData: ({ dispatch, path }) => () => {
      dispatch(get(path));
    },
    handleClick: ({
      s3,
      bucket,
      showPreview,
      expiration,
    }) => async (path) => {
      if (ContentWindow.supports(path)) {
        showPreview(path);
      } else {
        const url = s3.getSignedUrl('getObject', {
          Bucket: bucket,
          Key: path,
          Expires: expiration,
        });
        window.open(url, '_blank');
      }
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
  ({
    prefix,
    state,
    result,
    getData,
    bucket,
    preview,
    expiration,
    hidePreview,
    handleClick,
  }) => (
    <div>
      <BreadCrumbs prefix={prefix} root={bucket} />
      {invoke(state, {
        FETCHING: () => (
          <Spinner style={{ fontSize: '3em' }} />
        ),
        ERROR: () => (
          <h3>
            <MIcon>warning</MIcon>
            Something went wrong
            <RaisedButton label="Retry" onClick={getData} />
          </h3>
        ),
        READY: () => (
          <React.Fragment>
            <Preview
              bucket={bucket}
              path={preview}
              expiration={expiration}
              hide={hidePreview}
            />
            <Listing
              path={prefix}
              directories={result.directories}
              files={result.files}
              onFileClick={handleClick}
            />
            {result.readme && (
              <SummaryItem
                title={withoutPrefix(prefix, result.readme)}
                bucket={bucket}
                path={result.readme}
                expiration={expiration}
              />
            )}
            {result.summary && (
              <Summary
                bucket={bucket}
                path={result.summary}
                expiration={expiration}
              />
            )}
          </React.Fragment>
        ),
      })}
    </div>
  ));
