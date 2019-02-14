import { boundMethod } from 'autobind-decorator';
import cx from 'classnames';
import PT from 'prop-types';
import * as React from 'react';
import * as RC from 'recompose';
import { withStyles } from '@material-ui/core/styles';
import embed from 'vega-embed';

import * as RT from 'utils/reactTools';


const Vega = RT.composeComponent('Preview.renderers.Vega',
  withStyles((t) => ({
    root: {
      padding: t.spacing.unit * 1.5,
    },
  })),
  RC.setPropTypes({
    spec: PT.object.isRequired,
  }),
  class extends React.Component {
    constructor() {
      super();
      this.state = { el: null };
    }

    componentDidMount() {
      this.embed();
    }

    componentDidUpdate(prevProps, prevState) {
      if (
        prevState.el !== this.state.el
        || prevProps.spec !== this.props.spec
      ) this.embed();
    }

    @boundMethod
    setEl(el) {
      this.setState({ el });
    }

    embed() {
      if (this.state.el) embed(this.state.el, this.props.spec, { actions: false });
    }

    render() {
      const { spec, classes, className, ...props } = this.props;
      return (
        <div
          ref={this.setEl}
          className={cx(className, classes.root)}
          {...props}
        />
      );
    }
  });

export default ({ spec }, props) => <Vega spec={spec} {...props} />;
