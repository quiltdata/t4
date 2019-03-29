import cx from 'classnames';
import * as R from 'ramda';
import * as React from 'react';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import { makeStyles } from '@material-ui/styles';


const COL_LIMIT = 250;

const useStyles = makeStyles((t) => ({
  root: {
    overflow: 'auto',
    padding: t.spacing.unit * 1.5,
  },
  table: {
    fontFamily: t.typography.monospace.fontFamily,
  },
  row: {
    height: t.spacing.unit * 3,
  },
  cell: {
    border: 'none',

    '&, &:last-child': {
      paddingLeft: t.spacing.unit * 2,
      paddingRight: 0,
    },

    '&:first-child': {
      paddingLeft: 0,
    },
  },
  meta: {
    color: t.palette.text.hint,
  },
  header: {
    color: t.palette.text.primary,
    fontWeight: 600,
  },
}));

const Skip = Symbol('Skip');
const compact = R.when(
  (l) => l.length > COL_LIMIT * 2,
  (l) => [...R.take(COL_LIMIT, l), Skip, ...R.takeLast(COL_LIMIT, l)],
);

// eslint-disable-next-line react/prop-types
const Vcf = ({ meta, header, data }) => {
  const classes = useStyles();

  const renderCell = (type, i) => (col, j) => (
    <TableCell
      // eslint-disable-next-line react/no-array-index-key
      key={`${type}:${i}:${j}`}
      className={cx(classes.cell, classes[type])}
    >
      {col === Skip ? <React.Fragment>&hellip;</React.Fragment> : col}
    </TableCell>
  );

  const compactHeader = React.useMemo(() => header.map(compact), [header]);
  const compactData = React.useMemo(() => data.map(compact), [data]);

  return (
    <div className={classes.root}>
      <Table className={classes.table}>
        <TableHead>
          {meta.map((l, i) => (
            // eslint-disable-next-line react/no-array-index-key
            <TableRow key={`meta:${i}`} className={classes.row}>
              <TableCell
                colSpan={header[0].length}
                className={cx(classes.cell, classes.meta)}
              >
                {l}
              </TableCell>
            </TableRow>
          ))}
          {compactHeader.map((row, i) => (
            // eslint-disable-next-line react/no-array-index-key
            <TableRow key={`header:${i}`} className={classes.row}>
              {row.map(renderCell('header', i))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {compactData.map((row, i) => (
            // eslint-disable-next-line react/no-array-index-key
            <TableRow key={`data:${i}`} className={classes.row}>
              {row.map(renderCell('data', i))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default (data, props) => <Vcf {...data} {...props} />;
