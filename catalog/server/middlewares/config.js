const { readFile } = require('fs');
const { resolve } = require('path');


const loadFile = (path) =>
  new Promise((res, rej) =>
    readFile(path, 'utf-8', (err, file) => err ? rej(err) : res(file)));

module.exports = (path) => {
  const dataP = loadFile(path);
  const tmplP = loadFile(resolve(__dirname, '../../config.js.tmpl'));

  return (_req, res, next) =>
    Promise
      .all([dataP, tmplP])
      .then(([data, tmpl]) => tmpl.replace('$data', data))
      .then((result) => res.type('js').send(result))
      .catch(next);
};
