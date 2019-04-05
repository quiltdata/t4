import cx from 'classnames';
import * as React from 'react';
import MuiTable from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableRow from '@material-ui/core/TableRow';
import { makeStyles } from '@material-ui/styles';


const useStyles = makeStyles((t) => ({
  root: {
    padding: t.spacing.unit * 1.5,
    width: '100%',
  },
  wrapper: {
    overflow: 'auto',
  },
  row: {
    height: t.spacing.unit * 3,

    '&:nth-child(even)': {
      background: t.palette.grey[100],
    },
  },
  cell: {
    border: 'none',
    whiteSpace: 'nowrap',

    '&, &:last-child': {
      paddingLeft: t.spacing.unit,
      paddingRight: t.spacing.unit,
    },
  },
  skip: {
    textAlign: 'center',
  },
}));

// eslint-disable-next-line react/prop-types
const Table = ({ head, tail, className, ...props }) => {
  const classes = useStyles();

  return (
    <div className={cx(className, classes.root)} {...props}>
      <div className={classes.wrapper}>
        <MuiTable>
          <TableBody>
            {head.map((row, i) => (
              // eslint-disable-next-line react/no-array-index-key
              <TableRow key={`head:${i}`} className={classes.row}>
                {row.map((col, j) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <TableCell key={`head:${i}:${j}`} className={classes.cell}>
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            ))}
            {!!tail.length && (
              <TableRow key="skip" className={classes.row}>
                <TableCell
                  colSpan={head[0].length}
                  className={cx(classes.cell, classes.skip)}
                >
                  &hellip; rows skipped &hellip;
                </TableCell>
              </TableRow>
            )}
            {tail.map((row, i) => (
              // eslint-disable-next-line react/no-array-index-key
              <TableRow key={`tail:${i}`} className={classes.row}>
                {row.map((col, j) => (
                  // eslint-disable-next-line react/no-array-index-key
                  <TableCell key={`tail:${i}:${j}`} className={classes.cell}>
                    {col}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </MuiTable>
      </div>
    </div>
  );
};

export default (table, props) => <Table {...table} {...props} />;
