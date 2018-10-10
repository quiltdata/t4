import { Card, CardText } from 'material-ui/Card';
import * as colors from 'material-ui/styles/colors';
import { ListItem } from 'material-ui/List';
import PT from 'prop-types';
import * as React from 'react';
import { Link } from 'react-router-dom';
import {
  setPropTypes,
  withProps,
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

const Item = composeComponent('Browser.Listing.Item',
  setPropTypes({
    icon: PT.string,
    text: PT.string,
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
        {!!icon && <MIcon style={{ fontSize: 16, marginRight: 4 }}>{icon}</MIcon>}
        {text}
      </ItemName>
      <ItemInfo>{children}</ItemInfo>
    </ListItem>
  ));

const ItemDir = composeComponent('Browser.Listing.ItemDir',
  setPropTypes({
    path: PT.string.isRequired,
    name: PT.string.isRequired,
  }),
  ({ path, name }) => (
    <Item
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

const ItemFile = composeComponent('Browser.Listing.ItemFile',
  setPropTypes({
    name: PT.string.isRequired,
    modified: PT.instanceOf(Date).isRequired,
    size: PT.number.isRequired,
    onClick: PT.func.isRequired,
  }),
  ({ name, size, modified, onClick }) => (
    <Item
      icon="insert_drive_file"
      text={name}
      onClick={onClick}
    >
      <FileInfoSize>{readableBytes(size)}</FileInfoSize>
      <FileInfoModified>{modified.toLocaleString()}</FileInfoModified>
    </Item>
  ));

const StatsContainer = styled.div`
  background: ${colors.lightBlue50};
  margin-left: -12px;
  margin-right: -12px;
  margin-top: -12px;
  padding-bottom: 8px;
  padding-left: 20px;
  padding-right: 20px;
  padding-top: 8px;
`;

const Stats = composeComponent('Browser.Listing.Stats',
  setPropTypes({
    files: PT.array.isRequired,
  }),
  withProps(({ files }) =>
    files.reduce((sum, file) => ({
      files: sum.files + 1,
      size: sum.size + file.size,
      modified: file.modified > sum.modified ? file.modified : sum.modified,
    }), {
      files: 0,
      size: 0,
      modified: 0,
    })),
  ({ files, size, modified }) => (
    <StatsContainer>
      {!!files && (
        <span>{files} files {readableBytes(size)}</span>
      )}
      {!!modified && (
        <span>Last modified {modified.toLocaleString()}</span>
      )}
    </StatsContainer>
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
      <CardText style={{ padding: 0 }}>
        <Stats files={files} />
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
