import cx from 'classnames';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { FormattedRelative } from 'react-intl';
import * as RC from 'recompose';
import * as RF from 'redux-form/immutable';
import Button from '@material-ui/core/Button';
import DialogActions from '@material-ui/core/DialogActions';
import DialogContent from '@material-ui/core/DialogContent';
import DialogTitle from '@material-ui/core/DialogTitle';
import Paper from '@material-ui/core/Paper';
import Switch from '@material-ui/core/Switch';
import MuiTable from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableRow from '@material-ui/core/TableRow';
import * as Icons from '@material-ui/icons';
import { withStyles } from '@material-ui/core/styles';

import * as Notifications from 'containers/Notifications';
import * as APIConnector from 'utils/APIConnector';
import * as Dialogs from 'utils/Dialogs';
import * as Cache from 'utils/ResourceCache';
import * as RT from 'utils/reactTools';
import * as validators from 'utils/validators';

import * as Form from './Form';
import * as Table from './Table';


/*
user mngmnt:
create: POST /api/users/create { username, email }
delete: POST /api/users/delete { username } (disabled)
change admin: POST /api/users/{grant,revoke}_admin { username }
change active: POST /api/users/{enable,disable} { username }
change role: POST /api/users/set_role { username, role }
*/

const Mono = withStyles((t) => ({
  root: {
    fontFamily: t.typography.monospace.fontFamily,
  },
}))(({ className, classes, ...props }) =>
  <span className={cx(className, classes.root)} {...props} />);

const Create = RT.composeComponent('Admin.Users.Create',
  RC.setPropTypes({
    close: PT.func.isRequired,
  }),
  ({ close }) => {
    const req = APIConnector.use();
    const cache = Cache.use();
    const { push } = Notifications.use();
    const onSubmit = React.useCallback(
      (values) =>
        req({
          endpoint: '/users/create',
          method: 'POST',
          body: JSON.stringify(values.toJS()),
        })
          .then(() => {
            const user = {
              dateJoined: new Date(),
              email: values.get('email'),
              isActive: true,
              isAdmin: false,
              lastLogin: new Date(),
              username: values.get('username'),
            };
            cache.patchOk(UsersResource, null, R.append(user));
            push(`User "${user.username}" <${user.email}> created`);
            close();
          })
          .catch((e) => {
            if (APIConnector.HTTPError.is(e, 400, /Username is not valid/)) {
              throw new RF.SubmissionError({ username: 'invalid' });
            }
            if (APIConnector.HTTPError.is(e, 409, /Username already taken/)) {
              throw new RF.SubmissionError({ username: 'taken' });
            }
            if (APIConnector.HTTPError.is(e, 400, /Invalid email/)) {
              throw new RF.SubmissionError({ email: 'invalid' });
            }
            if (APIConnector.HTTPError.is(e, 409, /Email already taken/)) {
              throw new RF.SubmissionError({ email: 'taken' });
            }
            // eslint-disable-next-line no-console
            console.error('Error creating user');
            // eslint-disable-next-line no-console
            console.dir(e);
            throw new RF.SubmissionError({ _error: 'unexpected' });
          }),
      [req, cache, push, close],
    );

    return (
      <Form.ReduxForm form="Admin.Users.Create" onSubmit={onSubmit}>
        {({ handleSubmit, submitting, submitFailed, error, invalid }) => (
          <React.Fragment>
            <DialogTitle>Create a user</DialogTitle>
            <DialogContent>
              <form onSubmit={handleSubmit}>
                <RF.Field
                  component={Form.Field}
                  name="username"
                  validate={[validators.required]}
                  placeholder="Username"
                  fullWidth
                  margin="normal"
                  errors={{
                    required: 'Enter a username',
                    taken: 'Username already taken',
                    invalid: (
                      <span>
                        Enter a
                        {' '}
                        <abbr
                          title="Must start with a letter or underscore, and contain only alphanumeric characters and underscores thereafter"
                        >
                          valid
                        </abbr>
                        {' '}
                        username
                      </span>
                    ),
                  }}
                />
                <RF.Field
                  component={Form.Field}
                  name="email"
                  validate={[validators.required]}
                  placeholder="Email"
                  fullWidth
                  margin="normal"
                  errors={{
                    required: 'Enter an email',
                    taken: 'Email already taken',
                    invalid: 'Enter a valid email',
                  }}
                />
                {submitFailed && (
                  <Form.FormError
                    error={error}
                    errors={{
                      unexpected: 'Something went wrong',
                    }}
                  />
                )}
                <input type="submit" style={{ display: 'none' }} />
              </form>
            </DialogContent>
            <DialogActions>
              <Button
                onClick={() => close('cancel')}
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
      </Form.ReduxForm>
    );
  });

const Delete = RT.composeComponent('Admin.Users.Delete',
  RC.setPropTypes({
    user: PT.object.isRequired,
    close: PT.func.isRequired,
  }),
  ({ user, close }) => {
    const req = APIConnector.use();
    const cache = Cache.use();
    const { push } = Notifications.use();
    const doDelete = React.useCallback(() => {
      close();
      req({
        endpoint: '/users/delete',
        method: 'POST',
        body: JSON.stringify({ username: user.username }),
      })
        .then(() => {
          push(`User "${user.username}" deleted`);
        })
        .catch((e) => {
          // TODO: handle errors once the endpoint is working
          cache.patchOk(UsersResource, null, R.append(user));
          push(`Error deleting user "${user.username}"`);
          // eslint-disable-next-line no-console
          console.error('Error deleting user');
          // eslint-disable-next-line no-console
          console.dir(e);
        });
      // optimistically remove the user from cache
      cache.patchOk(UsersResource, null,
        R.reject(R.propEq('username', user.username)));
    }, [user, close, req, cache, push]);

    return (
      <React.Fragment>
        <DialogTitle>Delete a user</DialogTitle>
        <DialogContent>
          You are about to delete the &quot;{user.username}&quot; user.
          This operation is irreversible.
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => close('cancel')}
            color="primary"
          >
            Cancel
          </Button>
          <Button
            onClick={doDelete}
            color="primary"
          >
            Delete
          </Button>
        </DialogActions>
      </React.Fragment>
    );
  });

const UsersResource = Cache.createResource({
  name: 'Admin.Users.uesrs',
  fetch: ({ req }) =>
    req({ endpoint: '/users/list' })
      .then(R.pipe(
        R.prop('results'),
        R.map((u) => ({
          dateJoined: new Date(u.date_joined),
          email: u.email,
          isActive: u.is_active,
          isAdmin: u.is_superuser,
          lastLogin: new Date(u.last_login),
          username: u.username,
        })),
      )),
  key: () => null,
});

const Username = RT.composeComponent('Admin.Users.Username',
  RC.setPropTypes({
    admin: PT.bool,
  }),
  withStyles((t) => ({
    root: {
      position: 'relative',
    },
    admin: {
      fontWeight: 600,

      '&::before': {
        color: t.palette.secondary.main,
        content: '"*"',
        position: 'absolute',
        right: 'calc(100% + 0.2em)',
      },
    },
  })),
  ({ className, classes, admin = false, ...props }) => (
    <Mono
      className={cx(className, classes.root, { [classes.admin]: admin })}
      {...props}
    />
  ));

const Users = () => {
  const columns = React.useMemo(() => [
    {
      id: 'username',
      label: 'Username',
      getValue: R.prop('username'),
      getDisplay: (v, u) => <Username admin={u.isAdmin}>{v}</Username>,
      props: { component: 'th', scope: 'row' },
    },
    {
      id: 'email',
      label: 'Email',
      getValue: R.prop('email'),
    },
    {
      id: 'role',
      label: 'Role',
      getValue: () => '<TBD>',
      // TODO: dropdown
    },
    {
      id: 'isActive',
      label: 'Active',
      getValue: R.prop('isActive'),
      getDisplay: (v) => <Switch checked={v} />,
    },
    {
      id: 'isAdmin',
      label: 'Admin',
      getValue: R.prop('isAdmin'),
      getDisplay: (v) => <Switch checked={v} />,
    },
    // {
    //   id: 'searchEnabled',
    //   label: 'Search enabled',
    //   getValue: () => true,
    //   getDisplay: (v) => <Switch checked={v} />,
    // },
    {
      id: 'dateJoined',
      label: 'Date joined',
      getValue: R.prop('dateJoined'),
      getDisplay: (v) => <FormattedRelative value={v} />,
    },
    {
      id: 'lastLogin',
      label: 'Last login',
      getValue: R.prop('lastLogin'),
      getDisplay: (v) => <FormattedRelative value={v} />,
    },
  ], []);

  const req = APIConnector.use();
  const rows = Cache.useData(UsersResource, { req }, { suspend: true });

  const ordering = Table.useOrdering({ rows, column: columns[0] });
  const dialogs = Dialogs.use();

  const toolbarActions = [
    {
      title: 'Create',
      icon: <Icons.Add />,
      fn: React.useCallback(() => {
        dialogs.open(({ close }) => <Create {...{ close }} />);
      }, [dialogs.open]),
    },
  ];

  const inlineActions = (user) => [
    {
      title: 'Delete',
      icon: <Icons.Delete />,
      fn: () => {
        dialogs.open(({ close }) => <Delete {...{ user, close }} />);
      },
    },
    // {
    //  title: 'Edit',
    //  icon: <Icons.Edit />,
    //  fn: () => {
    //  },
    // },
  ];

  return (
    <Paper>
      {dialogs.render()}
      <Table.Toolbar heading="Users" actions={toolbarActions} />
      <Table.Wrapper>
        <MuiTable padding="dense">
          <Table.Head columns={columns} ordering={ordering} withInlineActions />
          <TableBody>
            {ordering.ordered.map((i) => (
              <TableRow hover key={i.username}>
                {columns.map((col) => (
                  <TableCell key={col.id} {...col.props}>
                    {(col.getDisplay || R.identity)(col.getValue(i), i)}
                  </TableCell>
                ))}
                <Table.InlineActions actions={inlineActions(i)} />
              </TableRow>
            ))}
          </TableBody>
        </MuiTable>
      </Table.Wrapper>
    </Paper>
  );
};

const Placeholder = () => (
  <Paper>
    <Table.Toolbar heading="Users" />
    <Table.Progress />
  </Paper>
);

export default () => (
  <React.Suspense fallback={<Placeholder />}>
    <Users />
  </React.Suspense>
);
