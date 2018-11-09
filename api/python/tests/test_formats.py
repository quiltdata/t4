#! /usr/bin/python
# -*- coding: utf-8 -*-

""" Docstring

"""

### Compatibility Block
# Make python 2.x behave as much like python3 as possible.  Ignore in python3
from __future__ import absolute_import, division, unicode_literals, print_function, nested_scopes

try:
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    input = raw_input
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    range = xrange
    # noinspection PyShadowingBuiltins,PyUnresolvedReferences
    str = unicode
    # noinspection PyUnresolvedReferences,PyCompatibility
    from future_builtins import *
except (ImportError, NameError):
    pass

__author__ = 'Brian Visel <eode@eptitude.net>'

### Python imports
import pathlib

### Third Party imports

### Project imports
from t4.formats import Formats

### Constants


### Code
def test_formats():
    testdir = pathlib.Path(__file__).parent
    import numpy as np

    arr = np.ndarray(3)

    fmt = Formats.for_obj(arr)

    assert 'npz' in fmt._handled_extensions
    assert Formats.for_ext('npy') is fmt
    assert len(Formats.for_obj('blah', single=False)) == 2   # json, unicode
    bytes_obj = fmt.serialize(arr)
    assert np.array_equal(fmt.deserialize(bytes_obj), arr)



