import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';

import * as RT from 'utils/reactTools';
import usePrevious from 'utils/usePrevious';


const PER_PAGE = 10;

const useGetter = (value, get) =>
  React.useMemo(() => value == null ? value : get(value), [value, get]);

const useHasChanged = (value, getKey = R.identity) => {
  const key = useGetter(value, getKey);
  const oldValue = usePrevious(value);
  const oldKey = useGetter(oldValue, getKey);
  return !R.equals(key, oldKey);
};

export const use = (items, {
  getItemId = R.identity,
  perPage = PER_PAGE,
  onChange,
} = {}) => {
  const pages = Math.max(1, Math.ceil(items.length / perPage));

  const [page, setPage] = React.useState(1);
  const nextPage = React.useCallback(
    () => setPage(Math.min(pages, page + 1)),
    [setPage, pages, page],
  );
  const prevPage = React.useCallback(
    () => setPage(Math.max(1, page - 1)),
    [setPage, page],
  );
  const goToPage = setPage;

  const getKey = useGetter(getItemId, R.map);
  if (useHasChanged(items, getKey) && page !== 1) {
    // reset to page 1 if items change
    goToPage(1);
  }

  const offset = (page - 1) * perPage;

  const paginated = useGetter(items, R.slice(offset, offset + perPage));

  usePrevious(page, (prev) => {
    if (page !== prev && onChange) onChange(prev, page);
  });

  // eslint-disable-next-line object-curly-newline
  return { paginated, page, pages, nextPage, prevPage, goToPage };
};

export const Paginate = RT.composeComponent('Pagination.Paginate',
  RC.setPropTypes({
    items: PT.array.isRequired,
    children: PT.func.isRequired,
  }),
  ({ items, children, ...props }) => children(use(items, props)));
