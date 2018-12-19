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


NEW_INDENTATION_LEVEL = -1


def escape(text, esc_chars=(r'\*_')):
  for char in esc_chars:
    text = text.replace(char, '\\' + char)
  return text


class Preprocessor(object):
  """
  This class implements the basic preprocessing.
  """

  def __init__(self, config):
    self.config = config
    self.indents = []
    self.doctest_indent = 0
    self.codeblock_indent = None
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
      section.title = escape(sig)

    self.lines = []
    current_section = None
    for line in section.content.split('\n'):
      line, current_section = self._preprocess_line(line, current_section, section)
      self.lines.append(line)
    section.content = self._preprocess_refs('\n'.join(self.lines))

  def _preprocess_line(self, line, current_section, section):
    if not line.strip():
      return line, current_section
    indent = get_indent(line)

    if self.indents:
      # if expected and found an indent, add an indent level.
      if self.indents[-1] == NEW_INDENTATION_LEVEL:
        # NEW_INDENTATION_LEVEL means a section title was parsed and a new level is
        # expected.
        del self.indents[-1]
        # make sure the section title has a blank line following it
        if self.lines[-1].strip():
          #self.lines.append('')
          pass
        if not self.indents or self.indents and indent > self.indents[-1]:
          self.indents.append(indent)
    while self.indents and indent < self.indents[-1]:
      del self.indents[-1]

    # handle codeblock indents
    if self.codeblock_indent is None:
      # start
      if line.lstrip().startswith('```'):
        self.codeblock_indent = indent
        return line[self.codeblock_indent:], current_section
    else:
      # continue / end
      if indent >= self.codeblock_indent:
        line = line[self.codeblock_indent:]
        # end
        if line.lstrip().startswith('```'):
          self.codeblock_indent = None
        return line, current_section
      else:
        print("Warning, malformed codeblock in: " + section.title)
        if line.lstrip().startswith('```'):
          self.codeblock_indent = None
        return line, current_section

    # handle doctest-style strings.
    level = self.indents[-1] if self.indents else 0
    if not self.doctest_indent:
      if is_doctest_start(line) and level < indent:
        # start
        self.lines.append('```python')
        self.indents.append(indent)
        self.doctest_indent = indent
        return line, current_section
    elif level >= self.doctest_indent:
        # continue
        return line, current_section
    else:
      # end
      self.doctest_indent = 0
      self.lines.append('```')

    # Check titles..
    match = re.match(r'^(\w.*):$', line.rstrip())
    if match:
      assert level == 0
      sec_name = match.group(1).strip().lower()
      if sec_name in self.valid_sections:
        current_section = self.valid_sections[sec_name]
        line = '__{}__\n'.format(current_section)
        self.indents.append(NEW_INDENTATION_LEVEL)
        return line, current_section

    line = line[level:]  # strip indents that have been accounted for.

    # TODO: Parse type names in parentheses after the argument/attribute name.
    if current_section in ('Arguments',):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '* __{}__: {}'.format(escape(a), b)
    elif current_section in ('Attributes', 'Raises'):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '* `{}`: {}'.format(escape(a), b)
    elif current_section in ('Returns', 'Yields'):
      if ':' in line:
        a, b = line.strip().split(':', 1)
        if all((a.strip(), b.strip())):
          line = '`{}`:{}'.format(escape(a), b)

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


def get_indent(line):
  whitespace = re.match(r'\s*', line).group(0).replace('\t', 8*' ')
  assert '\n' not in whitespace
  return len(whitespace)


def is_doctest_start(line):
  return  line.split(None, 1)[0] == '>>>'
