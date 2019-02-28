// import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import { FormattedRelative } from 'react-intl';
// import * as RC from 'recompose';
// import * as RF from 'redux-form/immutable';
// import Button from '@material-ui/core/Button';
// import DialogActions from '@material-ui/core/DialogActions';
// import DialogContent from '@material-ui/core/DialogContent';
// import DialogTitle from '@material-ui/core/DialogTitle';
import Paper from '@material-ui/core/Paper';
import Switch from '@material-ui/core/Switch';
import MuiTable from '@material-ui/core/Table';
import TableBody from '@material-ui/core/TableBody';
import TableCell from '@material-ui/core/TableCell';
import TableRow from '@material-ui/core/TableRow';
import * as Icons from '@material-ui/icons';
import { withStyles } from '@material-ui/core/styles';

// import * as Notifications from 'containers/Notifications';
import * as APIConnector from 'utils/APIConnector';
// import * as Dialogs from 'utils/Dialogs';
import * as Cache from 'utils/ResourceCache';
// import * as RT from 'utils/reactTools';
// import * as validators from 'utils/validators';

// import * as Form from './Form';
import * as Table from './Table';


const Mono = withStyles((t) => ({
  root: {
    fontFamily: t.typography.monospace.fontFamily,
  },
}))(({ classes, children }) =>
  <span className={classes.root}>{children}</span>);

const columns = [
  {
    id: 'username',
    label: 'Username',
    getValue: R.prop('username'),
    getDisplay: (v) => <Mono>{v}</Mono>,
    props: { component: 'th', scope: 'row' },
  },
  {
    id: 'email',
    label: 'Email',
    getValue: R.prop('email'),
  },
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
  {
    id: 'isActive',
    label: 'Active',
    getValue: R.prop('isActive'),
    getDisplay: (v) => <Switch checked={v} />,
  },
  {
    id: 'isSuperuser',
    label: 'Admin',
    getValue: R.prop('isSuperuser'),
    getDisplay: (v) => <Switch checked={v} />,
  },
];


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
          isSuperuser: u.is_superuser,
          lastLogin: new Date(u.last_login),
          username: u.username,
        })),
      )),
  key: () => null,
});

const Users = () => {
  const req = APIConnector.use();
  const rows = Cache.useData(UsersResource, { req }, { suspend: true });

  const ordering = Table.useOrdering({ rows, column: columns[0] });

  const toolbarActions = [
    {
      title: 'Create',
      icon: <Icons.Add />,
      fn: () => {
      },
    },
  ];

  const inlineActions = (/* user */) => [
    {
      title: 'Delete',
      icon: <Icons.Delete />,
      fn: () => {
      },
    },
    {
      title: 'Edit',
      icon: <Icons.Edit />,
      fn: () => {
      },
    },
  ];

  return (
    <Paper>
      <Table.Toolbar heading="Users" actions={toolbarActions} />
      <Table.Wrapper>
        <MuiTable>
          <Table.Head columns={columns} ordering={ordering} withInlineActions />
          <TableBody>
            {ordering.ordered.map((i) => (
              <TableRow hover key={i.username}>
                {columns.map((col) => (
                  <TableCell key={col.id} {...col.props}>
                    {(col.getDisplay || R.identity)(col.getValue(i))}
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
