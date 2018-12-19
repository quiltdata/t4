# Copyright (c) 2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
This module implements preprocessing Google + Markdown-like docstrings and
converts it to fully markdown compatible markup.
"""

import re


class Preprocessor(object):
  """
  This class implements the basic preprocessing.
  """

  def __init__(self, config):
    self.config = config
    self.indent = 0
    self.valid_sections = {
      'args': 'Arguments',
      'arguments': 'Arguments',
      'parameters': 'Arguments',
      'params': 'Arguments',
      'attributes': 'Attributes',
      'members': 'Attributes',
      'raises': 'Raises',
      'return': 'Returns',
      'returns': 'Returns',
      'yields': 'Yields',
    }

  def preprocess_section(self, section):
    """
    Preprocess the contents of *section*.
    """
    sig = section.loader_context.get('sig')
    if sig:
      # sig is not markdown.  Any '_*\' should be escaped.
      for char in r'\*_':
        sig = sig.replace(char, '\\' + char)
      section.title = sig

    lines = []
    codeblock_opened = False
    current_section = None
    for line in section.content.split('\n'):
      if line.startswith("```"):
        codeblock_opened = (not codeblock_opened)
      if not codeblock_opened:
        line, current_section = self._preprocess_line(line, current_section)
      lines.append(line)
    section.content = self._preprocess_refs('\n'.join(lines))

  def _preprocess_line(self, line, current_section):
    if not line.strip():
      return line, current_section

    match = re.match(r'^(.+):$', line.rstrip())
    if match:
      sec_name = match.group(1).strip().lower()
      if sec_name in self.valid_sections:
        current_section = self.valid_sections[sec_name]
        line = '__{}__\n'.format(current_section)
        self.indent = -1
        return line, current_section

    # check indent level.
    match = re.match('(\s+)', line)
    whitespace = ''
    if match:
      whitespace = match.group(1)
    if self.indent == -1:
      # this should be the first line with content after a section start.
      self.indent = len(whitespace)
    else:
      if len(whitespace) < self.indent:
        # indentation reduced, section ends.
        current_section = None
        # we're not handling nested sections
        self.indent = 0
    line = line[self.indent:]

    # TODO: Parse type names in parentheses after the argument/attribute name.
    if current_section in ('Arguments',):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '* __{}__: {}'.format(a, b)
    elif current_section in ('Attributes', 'Raises'):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '* `{}`: {}'.format(a, b)
    elif current_section in ('Returns', 'Yields'):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '`{}`:{}'.format(a, b)

    return line, current_section

  def _preprocess_refs(self, content):
    # TODO: Generate links to the referenced symbols.
    def handler(match):
      ref = match.group('ref')
      parens = match.group('parens') or ''
      has_trailing_dot = False
      if not parens and ref.endswith('.'):
        ref = ref[:-1]
        has_trailing_dot = True
      result = '`{}`'.format(ref + parens)
      if has_trailing_dot:
        result += '.'
      return (match.group('prefix') or '') + result
    return re.sub('(?P<prefix>^| |\t)#(?P<ref>[\w\d\._]+)(?P<parens>\(\))?', handler, content)
