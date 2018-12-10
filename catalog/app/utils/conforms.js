import * as R from 'ramda';


export default R.pipe(
  R.toPairs,
  R.map(([k, pred]) => R.propSatisfies(pred, k)),
  R.allPass,
);
