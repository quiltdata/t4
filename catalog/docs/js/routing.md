# Routing via `react-router` and `connected-react-router`

`react-router` is the de-facto standard routing solution for react applications.
The thing is that with redux and a single state tree, the URL is part of that
state. `connected-react-router` takes care of synchronizing the location of our
application with the application state.

(See the [`connected-react-router` documentation](https://github.com/supasate/connected-react-router)
for more information)

## Usage

To add a new route, modify the `App` container.

To go to a new page use the `push` function by `connected-react-router`:

```JS
import { push } from 'connected-react-router/immutable';

dispatch(push('/some/page'));
```
