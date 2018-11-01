import { basename } from 'path';

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
        flexWrap: 'wrap',
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
    path: PT.string.isRequired,
    modified: PT.instanceOf(Date).isRequired,
    size: PT.number.isRequired,
  }),
  ({ path, size, modified }) => (
    <Item
      icon="insert_drive_file"
      text={basename(path)}
      link={`/browse/${path}`}
    >
      <FileInfoSize>{readableBytes(size)}</FileInfoSize>
      <FileInfoModified>{modified.toLocaleString()}</FileInfoModified>
    </Item>
  ));

const StatsContainer = styled.div`
  background: ${colors.grey50};
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  padding: 8px;
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
      <span>{files} files / {readableBytes(size)}</span>
      {!!modified && (
        <span>Last modified {modified.toLocaleString()}</span>
      )}
    </StatsContainer>
  ));

export default composeComponent('Browser.Listing',
  setPropTypes({
    prefix: PT.string.isRequired,
    directories: PT.array.isRequired,
    files: PT.array.isRequired,
  }),
  ({ prefix, directories, files }) => (
    <Card>
      <CardText style={{ padding: 0 }}>
        <Stats files={files} />
        {prefix !== '' && <ItemDir path={up(prefix)} name=".." />}
        {directories.map((d) => (
          <ItemDir
            key={d}
            path={d}
            name={ensureNoSlash(withoutPrefix(prefix, d))}
          />
        ))}
        {files.map(({ key, modified, size }) => (
          <ItemFile
            key={key}
            path={key}
            size={size}
            modified={modified}
          />
        ))}
      </CardText>
    </Card>
  ));
