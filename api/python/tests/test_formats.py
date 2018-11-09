#! /usr/bin/python
# -*- coding: utf-8 -*-

### Python imports
import pathlib

### Third Party imports

### Project imports
from t4.formats import Formats

### Constants


### Code
def test_buggy_parquet():
    """
    Test that T4 avoids crashing on bad Pandas metadata from
    old pyarrow libaries.
    """
    path = pathlib.Path(__file__).parent
    with open(path / 'data' / 'buggy_parquet.parquet', 'rb') as bad_parq:
        # Make sure this doesn't crash.
        fmt = Formats.registered_formats['pyarrow']
        fmt.deserialize(bad_parq.read())

def test_formats_for_obj():
    import numpy as np

    arr = np.ndarray(3)

    fmt = Formats.for_obj(arr)

    assert 'npz' in fmt._handled_extensions
    assert Formats.for_ext('npy') is fmt
    assert len(Formats.for_obj('blah', single=False)) == 2   # json, unicode
    bytes_obj = fmt.serialize(arr)
    assert np.array_equal(fmt.deserialize(bytes_obj), arr)


def test_formats_for_ext():
    fmt = Formats.for_ext('json')
    assert fmt.serialize({'blah': 'blah'}) == b'{"blah": "blah"}'
    assert fmt.deserialize(b'{"meow": "mix"}') == {'meow': 'mix'}


def test_formats_for_meta():
    bytes_fmt = Formats.for_meta({'target': 'bytes'})
    json_fmt = Formats.for_meta({'target': 'json'})

    some_bytes = b'["phlipper", "piglet"]'
    assert bytes_fmt.serialize(some_bytes) == some_bytes
    assert json_fmt.deserialize(some_bytes) == ['phlipper', 'piglet']


def test_formats_match():
    bytes_fmt = Formats.match('bytes')
    json_fmt = Formats.match('json')

    some_bytes = b'["phlipper", "piglet"]'
    assert bytes_fmt.serialize(some_bytes) == some_bytes
    assert json_fmt.deserialize(some_bytes) == ['phlipper', 'piglet']
