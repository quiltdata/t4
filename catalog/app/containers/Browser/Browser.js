import { basename, extname } from 'path';

import invoke from 'lodash/fp/invoke';
import { Card, CardTitle, CardText } from 'material-ui/Card';
import { ListItem } from 'material-ui/List';
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
import styled from 'styled-components';

import Markdown from 'components/Markdown';
import MIcon from 'components/MIcon';
import Spinner from 'components/Spinner';
import config from 'constants/config';
import { S3 } from 'utils/AWS';
import { composeComponent } from 'utils/reactTools';
import { injectReducer } from 'utils/ReducerInjector';
import {
  ensureNoSlash,
  up,
  splitPath,
  withoutPrefix,
} from 'utils/s3paths';
import { injectSaga } from 'utils/SagaInjector';
import { readableBytes } from 'utils/string';

import { get } from './actions';
import { REDUX_KEY } from './constants';
import saga from './saga';
import selector from './selectors';
import reducer from './reducer';


const IMAGE_EXTS = new Set([
  '.jpg', '.jpeg', '.png', '.gif',
]);

const ItemName = styled.div`
  display: flex;
`;

const ItemInfo = styled.div`
  display: flex;
`;

const ItemRow = composeComponent('Browser.ItemRow',
  setPropTypes({
    icon: PT.string.isRequired,
    text: PT.string.isRequired,
    link: PT.string,
    children: PT.node,
  }),
  ({ icon, text, link, children, ...props }) => (
    <ListItem
      containerElement={link ? <Link to={link} /> : undefined}
      innerDivStyle={{
        display: 'flex',
        fontSize: 14,
        justifyContent: 'space-between',
        padding: 8,
      }}
      {...props}
    >
      <ItemName>
        <MIcon style={{ fontSize: 16, marginRight: 4 }}>{icon}</MIcon>
        {text}
      </ItemName>
      <ItemInfo>{children}</ItemInfo>
    </ListItem>
  ));

const ItemDir = composeComponent('Browser.ItemDir',
  setPropTypes({
    path: PT.string.isRequired,
    name: PT.string.isRequired,
  }),
  ({ path, name }) => (
    <ItemRow
      icon="folder_open"
      text={name}
      link={`/browse/${path}`}
    />
  ));

const FileInfoSize = styled.div`
  text-align: right;
  width: 6em;
`;

const FileInfoModified = styled.div`
  text-align: right;
  width: 12em;
`;

const FileShape = {
  path: PT.string.isRequired,
  modified: PT.instanceOf(Date).isRequired,
  size: PT.number.isRequired,
};

const ItemFile = composeComponent('Browser.ItemFile',
  setPropTypes({
    name: PT.string.isRequired,
    modified: PT.instanceOf(Date).isRequired,
    size: PT.number.isRequired,
    onClick: PT.func.isRequired,
  }),
  ({ name, size, modified, onClick }) => (
    <ItemRow
      icon="insert_drive_file"
      text={name}
      onClick={onClick}
    >
      <FileInfoSize>{readableBytes(size)}</FileInfoSize>
      <FileInfoModified>{modified.toLocaleString()}</FileInfoModified>
    </ItemRow>
  ));

const ImagePreview = styled.img`
  display: block;
  margin-left: auto;
  margin-right: auto;
  max-height: 100%;
  max-width: 100%;
  min-width: 20%;
`;

const Placeholder = () => (
  <Spinner
    style={{
      fontSize: '4em',
      position: 'absolute',
      left: 20,
    }}
  />
);

const PreviewDir = composeComponent('Browser.PreviewDir',
  setPropTypes({
    path: PT.string.isRequired,
    directories: PT.arrayOf(PT.string.isRequired).isRequired,
    files: PT.arrayOf(PT.shape(FileShape).isRequired).isRequired,
    readme: PT.shape({
      file: PT.shape(FileShape).isRequired,
      contents: PT.string.isRequired,
    }),
    s3: PT.object.isRequired,
    s3Bucket: PT.string.isRequired,
  }),
  withStateHandlers({
    preview: null,
  }, {
    showPreview: () => (type, data) => ({ preview: { type, data } }),
    hidePreview: () => () => ({ preview: null }),
  }),
  withHandlers({
    handlePreview: ({
      s3,
      s3Bucket,
      showPreview,
    }) => async (path) => {
      const url = s3.getSignedUrl('getObject', {
        Bucket: s3Bucket,
        Key: path,
      });
      const ext = extname(path).toLowerCase();
      if (IMAGE_EXTS.has(ext)) {
        showPreview('image', url);
      } else if (ext === '.html') {
        showPreview('iframe', url);
      } else if (ext === '.ipynb') {
        showPreview('iframe',
          `${config.aws.apiGatewayUrl}/preview?url=${encodeURIComponent(url)}`);
      } else if (ext === '.md') {
        showPreview('placeholder');
        // TODO: Move this to saga.js?
        const data = await s3.getObject({
          Bucket: s3Bucket,
          Key: path,
        }).promise();
        const body = data.Body.toString('utf-8');
        showPreview('md', body);
      } else {
        window.open(url, '_blank');
      }
    },
  }),
  ({
    path,
    directories,
    files,
    readme,
    hidePreview,
    handlePreview,
    preview,
  }) => (
    <React.Fragment>
      <Modal
        isOpen={!!preview}
        onRequestClose={() => hidePreview()}
      >
        {preview && invoke(preview.type, {
          md: () => <Markdown data={preview.data} />,
          placeholder: () => <Placeholder />,
          iframe: () => (
            <React.Fragment>
              <iframe
                sandbox=""
                title="Preview"
                src={preview.data}
                style={{
                  width: '100%',
                  height: '100%',
                  border: 'none',
                  position: 'relative',
                  zIndex: 1,
                }}
              />
              <Placeholder />
            </React.Fragment>
          ),
          image: () => <ImagePreview src={preview.data} />,
        })}
      </Modal>
      <Card>
        <CardText style={{ padding: 12 }}>
          {path !== '' && <ItemDir path={up(path)} name=".." />}
          {directories.map((d) => (
            <ItemDir
              key={d}
              path={d}
              name={ensureNoSlash(withoutPrefix(path, d))}
            />
          ))}
          {files.map(({ path: fPath, modified, size }) => (
            <ItemFile
              key={fPath}
              name={withoutPrefix(path, fPath)}
              size={size}
              modified={modified}
              onClick={() => handlePreview(fPath)}
            />
          ))}
        </CardText>
      </Card>
      {readme && (
        <Card style={{ marginTop: 16 }}>
          <CardTitle title={withoutPrefix(path, readme.file.path)} />
          <CardText>
            <Markdown data={readme.contents} />
          </CardText>
        </Card>
      )}
    </React.Fragment>
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
  withProps({ s3Bucket: config.aws.s3Bucket }),
  S3.inject(),
  injectSaga(REDUX_KEY, saga),
  injectReducer(REDUX_KEY, reducer),
  connect(selector),
  withProps(({ match: { params: { path } } }) => ({
    path,
    ...splitPath(path),
  })),
  withHandlers({
    getData: ({ dispatch, path }) => () => {
      dispatch(get(path));
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
    s3,
    s3Bucket,
  }) => (
    <div>
      <BreadCrumbs prefix={prefix} root={s3Bucket} />
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
          <PreviewDir
            path={prefix}
            {...result}
            s3={s3}
            s3Bucket={s3Bucket}
          />
        ),
      })}
    </div>
  ));
