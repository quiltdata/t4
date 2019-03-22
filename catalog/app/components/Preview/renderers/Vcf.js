import cx from 'classnames';
import * as React from 'react';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import { makeStyles } from '@material-ui/styles';


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

// eslint-disable-next-line react/prop-types
const Vcf = ({ meta, header, data }) => {
  const classes = useStyles();

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
          {header.map((row, i) => (
            // eslint-disable-next-line react/no-array-index-key
            <TableRow key={`header:${i}`} className={classes.row}>
              {row.map((col, j) => (
                <TableCell
                  // eslint-disable-next-line react/no-array-index-key
                  key={`header:${i}:${j}`}
                  className={cx(classes.cell, classes.header)}
                >
                  {col}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableHead>
        <TableBody>
          {data.map((row, i) => (
            // eslint-disable-next-line react/no-array-index-key
            <TableRow key={`data:${i}`} className={classes.row}>
              {row.map((col, j) => (
                // eslint-disable-next-line react/no-array-index-key
                <TableCell key={`data:${i}:${j}`} className={classes.cell}>
                  {col}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
};

export default (data, props) => <Vcf {...data} {...props} />;
