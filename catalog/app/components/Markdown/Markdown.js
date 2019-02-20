import cx from 'classnames';
import * as createDOMPurify from 'dompurify';
import hljs from 'highlight.js';
import memoize from 'lodash/memoize';
import PT from 'prop-types';
import * as R from 'ramda';
import * as React from 'react';
import * as RC from 'recompose';
import Remarkable from 'remarkable';
import { replaceEntities, escapeHtml, unescapeMd } from 'remarkable/lib/common/utils';
import { withStyles } from '@material-ui/core/styles';

import { linkStyle } from 'utils/StyledLink';
import * as RT from 'utils/reactTools';

const SANITIZE_OPTS = {
  'ALLOWED_TAGS': [
    'a',
    'abbr',
    'b',
    'blockquote',
    'code',
    'dd',
    'del',
    'div',
    'dl',
    'dt',
    'em',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'hr',
    'i',
    'img',
    'ins',
    'li',
    'mark',
    'ol',
    'p',
    'pre',
    'section',
    'span',
    'strong',
    'sub',
    'sup',
    'table',
    'tbody',
    'td',
    'thead',
    'tr',
    'ul',
  ],
  'FORBID_TAGS': ['style', 'script'],
  'FORBID_ATTR': ['style'],
};

// TODO: switch to pluggable react-aware renderer
// TODO: use react-router's Link component for local links
const highlight = (str, lang) => {
  if (lang === 'none') {
    return '';
  } else if (hljs.getLanguage(lang)) {
    try {
      return hljs.highlight(lang, str).value;
    } catch (err) {
      // istanbul ignore next
      console.error(err); // eslint-disable-line no-console
    }
  } else {
    try {
      return hljs.highlightAuto(str).value;
    } catch (err) {
      // istanbul ignore next
      console.error(err); // eslint-disable-line no-console
    }
  }
  // istanbul ignore next
  return ''; // use external default escaping
};

const escape = R.pipe(replaceEntities, escapeHtml);

/**
 * A Markdown (Remarkable) plugin. Takes a Remarkable instance and adjusts it.
 *
 * @typedef {function} MarkdownPlugin
 *
 * @param {Object} md Remarkable instance.
 */

/**
 * Create a plugin for remarkable that does custom processing of image tags.
 *
 * @param {Object} options
 * @param {bool} options.disable
 *   Don't show images, render them as they are in markdown contents (escaped).
 * @param {function} options.process
 *   Function that takes an image object ({ alt, src, title }) and returns a
 *   (possibly modified) image object.
 *
 * @returns {MarkdownPlugin}
 */
const imageHandler = ({
  disable = false,
  process = R.identity,
}) => (md) => {
  // eslint-disable-next-line no-param-reassign
  md.renderer.rules.image = (tokens, idx) => {
    const t = process(tokens[idx]);

    if (disable) {
      const alt = t.alt ? escape(t.alt) : '';
      const src = escape(t.src);
      const title = t.title ? ` "${escape(t.title)}"` : '';
      return `<span>![${alt}](${src}${title})</span>`;
    }

    const src = escapeHtml(t.src);
    const alt = t.alt ? escape(unescapeMd(t.alt)) : '';
    const title = t.title ? ` title="${escape(t.title)}"` : '';
    // TODO: rm inline width
    return `<img src="${src}" alt="${alt}"${title} width="33%"/>`;
  };
};

/**
 * Create a plugin for remarkable that does custom processing of links.
 *
 * @param {Object} options
 * @param {bool} options.nofollow
 *   Add rel="nofollow" attribute if true (default).
 * @param {function} options.process
 *   Function that takes a link object ({ href, title }) and returns a
 *   (possibly modified) link object.
 *
 * @returns {MarkdownPlugin}
 */
const linkHandler = ({
  nofollow = true,
  process = R.identity,
}) => (md) => {
  // eslint-disable-next-line no-param-reassign
  md.renderer.rules.link_open = (tokens, idx) => {
    const t = process(tokens[idx]);
    const title = t.title ? ` title="${escape(t.title)}"` : '';
    const rel = nofollow ? ' rel="nofollow"' : '';
    return `<a href="${escapeHtml(t.href)}"${rel}${title}>`;
  };
};

/**
 * Get Remarkable instance based on the given options (memoized).
 *
 * @param {Object} options
 *
 * @param {boolean} images
 *   Whether to render images notated as `![alt](src title)` or skip them.
 *
 * @returns {Object} Remarakable instance
 */
export const getRenderer = memoize(({
  images,
  processImg,
  processLink,
}) => {
  const md = new Remarkable('full', {
    highlight,
    html: true,
    linkify: true,
    typographer: true,
  });
  md.use(linkHandler({
    process: processLink,
  }));
  md.use(imageHandler({
    disable: !images,
    process: processImg,
  }));
  const purify = createDOMPurify(window);
  return (data) => purify.sanitize(md.render(data), SANITIZE_OPTS);
});

export const Container = RT.composeComponent('Markdown.Container',
  RC.setPropTypes({
    children: PT.string,
    className: PT.string,
  }),
  withStyles(() => ({
    root: {
      overflow: 'auto',

      '& h1 code': {
        backgroundColor: 'inherit',
      },

      /* prevent horizontal overflow */
      '& img': {
        maxWidth: '100%',
      },

      '& a': linkStyle,
    },
  })),
  ({ classes, className, children }) => (
    <div
      className={cx(className, classes.root)}
      // eslint-disable-next-line react/no-danger
      dangerouslySetInnerHTML={{ __html: children }}
    />
  ));

export default RT.composeComponent('Markdown',
  RC.setPropTypes({
    data: PT.string,
    images: PT.bool,
    processImg: PT.func,
    processLink: PT.func,
  }),
  ({ data, images = true, processImg, processLink, ...props }) => (
    <Container {...props}>
      {getRenderer({ images, processImg, processLink })(data)}
    </Container>
  ));
