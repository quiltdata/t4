import { Card, CardText } from 'material-ui/Card';
import { ListItem } from 'material-ui/List';
import PT from 'prop-types';
import * as React from 'react';
import { Link } from 'react-router-dom';
import {
  setPropTypes,
} from 'recompose';
import styled from 'styled-components';

import MIcon from 'components/MIcon';
import { composeComponent } from 'utils/reactTools';
import {
  ensureNoSlash,
  up,
  withoutPrefix,
} from 'utils/s3paths';
import { readableBytes } from 'utils/string';

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

export default composeComponent('Browser.Listing',
  setPropTypes({
    path: PT.string.isRequired,
    directories: PT.array.isRequired,
    files: PT.array.isRequired,
    onFileClick: PT.func.isRequired,
  }),
  ({ path, directories, files, onFileClick }) => (
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
            onClick={() => onFileClick(fPath)}
          />
        ))}
      </CardText>
    </Card>
  ));
