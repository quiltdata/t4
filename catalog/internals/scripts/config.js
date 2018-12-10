#!/usr/bin/env node

const { readFileSync } = require('fs');
const { resolve } = require('path');

const cfgPath = process.argv[2] || 'config.json';
const tmpl = readFileSync(resolve(__dirname, '../../config.js.tmpl'), 'utf-8');
const data = readFileSync(resolve(process.cwd(), cfgPath), 'utf-8');

process.stdout.write(tmpl.replace('$data', data));
