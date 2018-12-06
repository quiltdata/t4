import hljs from 'highlight.js';
import flow from 'lodash/flow';
import id from 'lodash/identity';
import memoize from 'lodash/memoize';
import PT from 'prop-types';
import React from 'react';
import { setPropTypes } from 'recompose';
import Remarkable from 'remarkable';
import { replaceEntities, escapeHtml, unescapeMd } from 'remarkable/lib/common/utils';
import styled from 'styled-components';

import { composeComponent } from 'utils/reactTools';


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

const escape = flow(replaceEntities, escapeHtml);

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
  process = id,
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
  process = id,
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
const getRenderer = memoize(({
  images,
  processImg,
  processLink,
}) => {
  const md = new Remarkable('full', {
    highlight,
    html: false,
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
  return md;
});

// Ensure that markdown styles are smaller than page h1, h2, etc. since
// they should appear as subordinate to the page's h1, h2
const Style = styled.div`
  display: block;
  overflow: auto;

  h1 code {
    background-color: inherit;
  }

  /* prevent horizontal overflow */
  img {
    max-width: 100%;
  }
`;

export default composeComponent('Markdown',
  setPropTypes({
    data: PT.string,
    className: PT.string,
    images: PT.bool,
    processImg: PT.func,
    processLink: PT.func,
  }),
  ({
    data,
    className = '',
    images = true,
    processImg,
    processLink,
  }) => (
    <Style
      className={`markdown ${className}`}
      dangerouslySetInnerHTML={{
        // would prefer to render in a saga but md.render() fails when called
        // in a generator
        __html:
          getRenderer({
            images,
            processImg,
            processLink,
          }).render(data),
      }}
    />
  ));
