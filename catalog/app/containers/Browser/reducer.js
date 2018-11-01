import AsyncResult from 'utils/AsyncResult';
import { withInitialState } from 'utils/reduxTools';
import tagged from 'utils/tagged';


export const Action = tagged([
  'Get', // {{ path: string, resolver: Resolver }}
  'GetResult', // AsyncResult
]);

export default withInitialState(AsyncResult.Init(), (s, a) =>
  Action.case({
    Get: () => AsyncResult.Pending(),
    // TODO: check if response corresponds to the current state (path)
    GetResult: (result) => result,
    __: () => s,
  }, a));
