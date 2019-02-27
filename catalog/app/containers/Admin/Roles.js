import cx from 'classnames';
import * as I from 'immutable';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import * as RF from 'redux-form/immutable';
import Button from '@material-ui/core/Button';
import Checkbox from '@material-ui/core/Checkbox';
import CircularProgress from '@material-ui/core/CircularProgress';
import Dialog from '@material-ui/core/Dialog';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import IconButton from '@material-ui/core/IconButton';
import Paper from '@material-ui/core/Paper';
import Table from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableHead from '@material-ui/core/TableHead';
import TableRow from '@material-ui/core/TableRow';
import TableSortLabel from '@material-ui/core/TableSortLabel';
import TextField from '@material-ui/core/TextField';
import Toolbar from '@material-ui/core/Toolbar';
import Tooltip from '@material-ui/core/Tooltip';
import Typography from '@material-ui/core/Typography';
import * as Icons from '@material-ui/icons';
import { withStyles } from '@material-ui/core/styles';
import { lighten } from '@material-ui/core/styles/colorManipulator';

import * as APIConnector from 'utils/APIConnector';
import * as Cache from 'utils/ResourceCache';
import * as RT from 'utils/reactTools';
import * as validators from 'utils/validators';


const RolesResource = Cache.createResource({
  fetch: ({ req }) => req({ endpoint: '/roles' }).then(R.prop('results')),
  key: () => null,
});

const Roles = () => {
  const req = APIConnector.use();
  const roles = Cache.use().get(RolesResource, { req });
  console.log('Roles', roles);
  return <RolesTable rows={roles} />;
};

const Mono = withStyles((t) => ({
  root: {
    fontFamily: t.typography.monospace.fontFamily,
  },
}))(({ classes, children }) =>
  <span className={classes.root}>{children}</span>);

const columns = [
  {
    id: 'name',
    label: 'Name',
    getValue: R.prop('name'),
    props: { component: 'th', scope: 'row' },
  },
  {
    id: 'arn',
    label: 'ARN',
    getValue: R.prop('arn'),
    getDisplay: (v) => <Mono>{v}</Mono>,
  },
];

const RolesHead = RT.composeComponent('Admin.Roles.Head',
  RC.setPropTypes({
    selection: PT.object.isRequired,
    ordering: PT.object.isRequired,
  }),
  ({ selection: sel, ordering: ord }) => (
    <TableHead>
      <TableRow>
        <TableCell
          padding="checkbox"
          onClick={sel.toggleAll}
        >
          <Checkbox
            indeterminate={
              sel.selected.size > 0
                && sel.selected.size < sel.all.size
            }
            checked={sel.selected.equals(sel.all)}
          />
        </TableCell>
        {columns.map((col) => (
          <TableCell
            key={col.id}
            sortDirection={ord.column === col ? ord.direction : false}
          >
            <Tooltip
              title="Sort"
              placement="bottom-start"
              enterDelay={300}
            >
              <TableSortLabel
                active={ord.column === col}
                direction={ord.direction}
                onClick={() => ord.change(col)}
              >
                {col.label}
              </TableSortLabel>
            </Tooltip>
          </TableCell>
        ))}
        <TableCell />
      </TableRow>
    </TableHead>
  ));

const RolesToolbar = RT.composeComponent('Admin.Roles.Toolbar',
  RC.setPropTypes({
    selected: PT.number.isRequired,
    onDeleteSelected: PT.func,
    onCreate: PT.func,
  }),
  withStyles((t) => ({
    root: {
      paddingRight: t.spacing.unit,
    },
    highlight:
      t.palette.type === 'light'
        ? {
          color: t.palette.secondary.main,
          backgroundColor: lighten(t.palette.secondary.light, 0.85),
        }
        : {
          color: t.palette.text.primary,
          backgroundColor: t.palette.secondary.dark,
        },
    spacer: {
      flex: '1 1 100%',
    },
    actions: {
      color: t.palette.text.secondary,
    },
    title: {
      flex: '0 0 auto',
    },
  })),
  ({ classes, selected, onCreate, onDeleteSelected }) => (
    <Toolbar
      className={cx(classes.root, {
        [classes.highlight]: selected > 0,
      })}
    >
      <div className={classes.title}>
        {selected > 0
          ? (
            <Typography color="inherit" variant="subtitle1">
              {selected} selected
            </Typography>
          )
          : (
            <Typography variant="h6">
              Roles
            </Typography>
          )}
      </div>
      <div className={classes.spacer} />
      {selected > 0
        ? (
          <div className={classes.actions}>
            {!!onDeleteSelected && (
              <Tooltip title="Delete">
                <IconButton aria-label="Delete" onClick={onDeleteSelected}>
                  <Icons.Delete />
                </IconButton>
              </Tooltip>
            )}
          </div>
        )
        : (
          <div className={classes.actions}>
            {!!onCreate && (
              <Tooltip title="Create">
                <IconButton aria-label="Create" onClick={onCreate}>
                  <Icons.Add />
                </IconButton>
              </Tooltip>
            )}
          </div>
        )}
    </Toolbar>
  ));


const changeDirection = (d) => d === 'asc' ? 'desc' : 'asc';

const useOrdering = ({ rows, ...opts }) => {
  const [column, setColumn] = React.useState(opts.column || columns[0]);
  const [direction, setDirection] = React.useState(opts.direction || 'asc');

  const sortBy = column.sortBy || column.getValue;
  const sort = React.useCallback(R.pipe(
    R.sortBy(sortBy),
    direction === 'asc' ? R.identity : R.reverse,
  ), [sortBy, direction]);

  const ordered = React.useMemo(() => sort(rows), [sort, ...rows]);

  const change = React.useCallback((newCol) => {
    if (column !== newCol) {
      setColumn(newCol);
      setDirection('asc');
    } else {
      setDirection(changeDirection);
    }
  }, [column, setColumn, setDirection]);

  return { column, direction, change, ordered };
};

const emptySet = I.Set();

const useSelection = ({ rows, getId = R.unary(I.fromJS) }) => {
  const [selected, setSelected] = React.useState(emptySet);
  const allSelected = React.useMemo(
    () => I.Set(rows.map(getId)),
    [rows, getId],
  );

  const toggle = React.useCallback((row) => {
    const id = getId(row);
    setSelected((s) => s.has(id) ? s.delete(id) : s.add(id));
  }, [setSelected, getId]);

  const toggleAll = React.useCallback(() => {
    setSelected((s) => s.equals(allSelected) ? emptySet : allSelected);
  }, [setSelected, allSelected]);

  const clear = React.useCallback(() => {
    setSelected(emptySet);
  }, [setSelected]);

  const isSelected = React.useCallback((row) => selected.has(getId(row)),
    [selected, getId]);

  // eslint-disable-next-line object-curly-newline
  return { toggle, toggleAll, clear, isSelected, selected, all: allSelected };
};

const RootPaper = RT.composeComponent('Admin.Roles.RootPaper',
  withStyles(() => ({
    root: {
      width: '100%',
    },
  })),
  Paper);

const Placeholder = RT.composeComponent('Admin.Roles.Placeholder',
  withStyles((t) => ({
    progress: {
      marginBottom: t.spacing.unit * 2,
      marginLeft: t.spacing.unit * 3,
    },
  })),
  ({ classes }) => (
    <RootPaper>
      <Toolbar>
        <Typography variant="h6">Roles</Typography>
      </Toolbar>
      <CircularProgress className={classes.progress} />
    </RootPaper>
  ));

const Field = RT.composeComponent('Admin.Roles.Field',
  RC.setPropTypes({
    input: PT.object.isRequired,
    meta: PT.object.isRequired,
    errors: PT.objectOf(PT.node),
  }),
  ({ input, meta, errors, ...rest }) => {
    const error = meta.submitFailed && meta.error;
    const props = {
      error: !!error,
      label: error ? errors[error] || error : undefined,
      ...input,
      ...rest,
    };
    return <TextField {...props} />;
  });

const FormError = RT.composeComponent('Admin.Roles.FormError',
  withStyles((t) => ({
    root: {
      marginTop: t.spacing.unit * 3,

      '& a': {
        textDecoration: 'underline',
      },
    },
  })),
  ({ submitFailed, error, errors, ...rest }) =>
    submitFailed && !!error && (
      <Typography color="error" {...rest}>{errors[error] || error}</Typography>
    ));

const ReduxForm = RF.reduxForm()(({ children, ...props }) => children(props));

const handleHttpError = (e, status, msg, fn) => {
  if (
    e instanceof APIConnector.HTTPError
      && e.status === status
      && e.json && e.json.message === msg
  ) {
    throw new RF.SubmissionError(fn(e));
  }
};

const Create = RT.composeComponent('Admin.Roles.Create',
  RC.setPropTypes({
    open: PT.bool.isRequired,
    onClose: PT.func.isRequired,
  }),
  ({ open, onClose }) => {
    const formRef = React.useRef(null);
    const close = React.useCallback(() => {
      if (formRef.current) formRef.current.reset();
      onClose();
    }, [onClose, formRef]);

    const req = APIConnector.use();
    const cache = Cache.use();
    const onSubmit = React.useCallback(
      (values) =>
        req({
          endpoint: '/roles',
          method: 'POST',
          body: JSON.stringify(values),
        })
          .then((res) => {
            console.log('created', res);
            cache.patchOk(RolesResource, null, R.append(res));
            close();
          })
          .catch((e) => {
            handleHttpError(e, 409, 'Role name already exists',
              () => ({ name: 'taken' }));
            handleHttpError(e, 400, 'Invalid name for role',
              () => ({ name: 'invalid' }));
            console.warn('Error creating role', e);
            throw new RF.SubmissionError({ _error: 'unexpected' });
          }),
      [req, cache, close],
    );

    return (
      <Dialog open={open} onClose={onClose}>
        <ReduxForm form="Admin.Roles.Create" onSubmit={onSubmit} ref={formRef}>
          {({ handleSubmit, submitting, submitFailed, error, invalid }) => (
            <React.Fragment>
              <DialogTitle>Create a role</DialogTitle>
              <DialogContent>
                <form onSubmit={handleSubmit}>
                  <RF.Field
                    component={Field}
                    name="name"
                    validate={[validators.required]}
                    disabled={submitting}
                    placeholder="Name"
                    fullWidth
                    margin="normal"
                    errors={{
                      required: 'Enter a role name',
                      taken: 'Role with this name already exists',
                      invalid: 'Invalid name for role',
                    }}
                  />
                  <RF.Field
                    component={Field}
                    name="arn"
                    validate={[validators.required]}
                    disabled={submitting}
                    placeholder="ARN"
                    fullWidth
                    margin="normal"
                    errors={{
                      required: 'Enter an ARN',
                    }}
                  />
                  <FormError
                    submitFailed={submitFailed}
                    error={error}
                    errors={{
                      unexpected: 'Something went wrong',
                    }}
                  />
                  <input type="submit" style={{ display: 'none' }} />
                </form>
              </DialogContent>
              <DialogActions>
                <Button
                  onClick={onClose}
                  color="primary"
                  disabled={submitting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleSubmit}
                  color="primary"
                  disabled={submitting || (submitFailed && invalid)}
                >
                  Create
                </Button>
              </DialogActions>
            </React.Fragment>
          )}
        </ReduxForm>
      </Dialog>
    );
  });

const RolesTable = RT.composeComponent('Admin.Roles.Table',
  RC.setPropTypes({
    rows: PT.array.isRequired,
  }),
  withStyles((t) => ({
    table: {
    },
    tableWrapper: {
      overflowX: 'auto',
    },
    row: {
    },
    actions: {
      textAlign: 'right',
      paddingRight: [t.spacing.unit, '!important'],

      '& > *': {
        opacity: 0,
        transition: 'opacity 100ms',

        '$row:hover &': {
          opacity: 1,
        },
      },
    },
  })),
  ({ classes, rows }) => {
    const ordering = useOrdering({ rows });
    const selection = useSelection({ rows });

    const [creating, setCreating] = React.useState(false);

    const deleteSelected = React.useCallback(() => {
      const selected = selection.selected.toJS();
      console.log('delete selected', selected);
      selection.clear();
    }, [selection.selected, selection.clear]);

    const edit = React.useCallback((i) => {
      console.log('edit', i);
    }, []);

    const remove = React.useCallback((i) => {
      console.log('remove', i);
    }, []);

    const startCreating = React.useCallback(() => {
      setCreating(true);
    }, [setCreating]);

    const finishCreating = React.useCallback(() => {
      setCreating(false);
    }, [setCreating]);

    return (
      <RootPaper>
        <Create open={creating} onClose={finishCreating} />

        <RolesToolbar
          selected={selection.selected.size}
          onDeleteSelected={deleteSelected}
          onCreate={startCreating}
        />
        <div className={classes.tableWrapper}>
          <Table className={classes.table}>
            <RolesHead selection={selection} ordering={ordering} />
            <TableBody>
              {ordering.ordered.map((i) => {
                const isSelected = selection.isSelected(i);
                return (
                  <TableRow
                    hover
                    key={i.id}
                    selected={isSelected}
                    className={classes.row}
                  >
                    <TableCell
                      padding="checkbox"
                      onClick={() => selection.toggle(i)}
                      role="checkbox"
                      aria-checked={isSelected}
                      tabIndex={-1}
                      selected={isSelected}
                    >
                      <Checkbox checked={isSelected} />
                    </TableCell>
                    {columns.map((col) => (
                      <TableCell key={col.id} {...col.props}>
                        {(col.getDisplay || R.identity)(col.getValue(i))}
                      </TableCell>
                    ))}
                    <TableCell className={classes.actions}>
                      <Tooltip title="Edit">
                        <IconButton aria-label="Edit" onClick={() => edit(i)}>
                          <Icons.Edit />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Delete">
                        <IconButton aria-label="Delete" onClick={() => remove(i)}>
                          <Icons.Delete />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </RootPaper>
    );
  });

export default () => (
  <React.Suspense fallback={<Placeholder />}>
    <Roles />
  </React.Suspense>
);
