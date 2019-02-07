import { basename } from 'path';

import hljs from 'highlight.js';
import * as R from 'ramda';

import { PreviewData } from '../types';
import * as utils from './utils';


const LANGS = {
  accesslog: /\.log$/,
  bash: /\.(ba|z)?sh$/,
  clojure: /\.clj$/,
  coffeescript: /\.(coffee|cson|iced)$/,
  coq: /\.v$/,
  cpp: /\.(c(c|\+\+|pp|xx)?)|(h(\+\+|pp|xx)?)$/,
  cs: /\.cs$/,
  css: /\.css$/,
  diff: /\.(diff|patch)$/,
  dockerfile: /^dockerfile$/,
  erlang: /\.erl$/,
  go: /\.go$/,
  haskell: /\.hs$/,
  ini: /\.(ini|toml)$/,
  java: /\.(java|jsp)$/,
  javascript: /\.m?jsx?$/,
  lisp: /\.lisp$/,
  makefile: /^(gnu)?makefile$/,
  matlab: /\.m$/,
  ocaml: /\.mli?$/,
  perl: /\.pl$/,
  php: /\.php[3-7]?$/,
  plaintext: /((^license)|(^readme)|(^\.\w*(ignore|rc|config))|(\.txt))$/,
  python: /\.(py|gyp)$/,
  r: /\.r$/,
  ruby: /\.rb$/,
  rust: /\.rs$/,
  scala: /\.scala$/,
  scheme: /\.s(s|ls|cm)$/,
  sql: /\.sql$/,
  typescript: /\.tsx?$/,
  xml: /\.(xml|x?html|rss|atom|xjb|xsd|xsl|plist)$/,
  yaml: /\.ya?ml$/,
};

const langPairs = Object.entries(LANGS);

const findLang = R.pipe(
  basename,
  R.toLower,
  (name) => langPairs.find(([, re]) => re.test(name)),
);

export const detect = R.pipe(findLang, Boolean);

const getLang = R.pipe(findLang, ([lang] = []) => lang);

export const load = utils.gatedS3Request(utils.objectGetter((r, { handle }) => {
  const contents = r.Body.toString('utf-8');
  const lang = getLang(handle.key);
  const highlighted = hljs.highlight(lang, contents).value;
  return PreviewData.Text({ contents, lang, highlighted });
}));
