#! /usr/bin/python
# -*- coding: utf-8 -*-

### Python imports
import pathlib

### Third Party imports
import numpy as np
import pandas as pd

### Project imports
from t4.formats import FormatsRegistry

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
        fmt = FormatsRegistry.registered_formats['pyarrow']
        fmt.deserialize(bad_parq.read())

def test_formats_for_obj():
    arr = np.ndarray(3)

    fmt = FormatsRegistry.for_obj(arr)

    assert 'npz' in fmt._handled_extensions
    assert FormatsRegistry.for_ext('npy') is fmt
    assert len(FormatsRegistry.for_obj('blah', single=False)) == 2   # json, unicode
    bytes_obj = fmt.serialize(arr)
    assert np.array_equal(fmt.deserialize(bytes_obj), arr)


def test_formats_for_ext():
    fmt = FormatsRegistry.for_ext('json')
    assert fmt.serialize({'blah': 'blah'}) == b'{"blah": "blah"}'
    assert fmt.deserialize(b'{"meow": "mix"}') == {'meow': 'mix'}


def test_formats_for_meta():
    bytes_fmt = FormatsRegistry.for_meta({'target': 'bytes'})
    json_fmt = FormatsRegistry.for_meta({'target': 'json'})

    some_bytes = b'["phlipper", "piglet"]'
    assert bytes_fmt.serialize(some_bytes) == some_bytes
    assert json_fmt.deserialize(some_bytes) == ['phlipper', 'piglet']


def test_formats_match():
    bytes_fmt = FormatsRegistry.match('bytes')
    json_fmt = FormatsRegistry.match('json')

    some_bytes = b'["phlipper", "piglet"]'
    assert bytes_fmt.serialize(some_bytes) == some_bytes
    assert json_fmt.deserialize(some_bytes) == ['phlipper', 'piglet']


def test_formats_serdes():
    objects = [
        {'blah': 'foo'},
        b'blather',
        'blip',
    ]
    metadata = [{} for o in objects]

    for obj, meta in zip(objects, metadata):
        assert FormatsRegistry.deserialize(FormatsRegistry.serialize(obj, meta), meta) == obj

    df = pd.DataFrame([[1, 2], [3, 4]])
    meta = {}
    assert df.equals(FormatsRegistry.deserialize(FormatsRegistry.serialize(df, meta), meta))






