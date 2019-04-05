import cx from 'classnames';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/styles';

import * as RT from 'utils/reactTools';


const Parquet = RT.composeComponent('Preview.renderers.Parquet',
  RC.setPropTypes({
    className: PT.string,
    preview: PT.string.isRequired,
    createdBy: PT.string,
    formatVersion: PT.string,
    metadata: PT.object,
    numRowGroups: PT.number,
    // { path, logicalType, physicalType, maxDefinitionLevel, maxRepetitionLevel }
    schema: PT.object.isRequired,
    serializedSize: PT.number,
    shape: PT.object, // { rows, columns }
  }),
  withStyles(({ palette, spacing: { unit }, typography }) => ({
    root: {
      padding: unit,
      width: '100%',
    },
    meta: {
    },
    metaName: {
      paddingRight: unit,
      textAlign: 'left',
    },
    metaValue: {
      fontFamily: typography.monospace,
    },
    dataframe: {
      overflow: 'auto',
      paddingTop: 2 * unit,

      '& table.dataframe': {
        border: 'none',
        width: 'auto',

        '& tr:nth-child(even)': {
          backgroundColor: palette.grey[100],
        },

        '& th, & td': {
          border: 'none',
          fontSize: 'small',
          height: 3 * unit,
          paddingLeft: unit,
          paddingRight: unit,
        },

        '& td': {
          whiteSpace: 'nowrap',
        },
      },
    },
  })),
  ({
    classes,
    className,
    preview,
    createdBy,
    formatVersion,
    metadata,
    numRowGroups,
    schema,
    serializedSize,
    shape,
    ...props
  }) => {
    // TODO: meta styling, json expansion
    const renderMeta = (name, value, render = R.identity) => !!value && (
      <tr>
        <th className={classes.metaName}>{name}</th>
        <td className={classes.metaValue}>{render(value)}</td>
      </tr>
    );

    /*
    const renderJson = (json) => (
      <div>{JSON.stringify(json)}</div>
    );
    */

    return (
      <div className={cx(className, classes.root)} {...props}>
        <table className={classes.meta}>
          <tbody>
            {renderMeta('Created by:', createdBy)}
            {renderMeta('Format version:', formatVersion)}
            {renderMeta('# row groups:', numRowGroups)}
            {renderMeta('Serialized size:', serializedSize)}
            {renderMeta('Shape:', shape, ({ rows, columns }) =>
              <span>{rows} rows &times; {columns} columns</span>)}
            {/*
            {renderMeta('Metadata:', metadata, renderJson)}
            {renderMeta('Schema:', schema, renderJson)}
            */}
          </tbody>
        </table>
        <div
          className={classes.dataframe}
          // eslint-disable-next-line react/no-danger
          dangerouslySetInnerHTML={{ __html: preview }}
        />
      </div>
    );
  });

export default (data, props) => <Parquet {...data} {...props} />;
