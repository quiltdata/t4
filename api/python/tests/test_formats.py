# -*- coding: utf-8 -*-

### Python imports
import pathlib

### Third Party imports
import numpy as np
import pandas as pd

### Project imports
from t4.formats import FormatRegistry

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
        fmt = FormatRegistry.registered_formats['pyarrow']
        fmt.deserialize(bad_parq.read())

def test_formats_for_obj():
    arr = np.ndarray(3)

    fmt = FormatRegistry.for_obj(arr)

    assert 'npz' in fmt.handled_extensions
    assert FormatRegistry.for_ext('npy') is fmt

    expected_string_fmt_names = ['utf-8', 'unicode', 'json']
    found_string_fmt_names = list(f.name for f in FormatRegistry.for_obj('blah', single=False))
    assert found_string_fmt_names == expected_string_fmt_names

    bytes_obj = fmt.serialize(arr)
    assert np.array_equal(fmt.deserialize(bytes_obj), arr)


def test_formats_for_ext():
    fmt = FormatRegistry.for_ext('json')
    assert fmt.serialize({'blah': 'blah'}) == b'{"blah": "blah"}'
    assert fmt.deserialize(b'{"meow": "mix"}') == {'meow': 'mix'}


def test_formats_for_meta():
    bytes_fmt = FormatRegistry.for_meta({'target': 'bytes'})
    json_fmt = FormatRegistry.for_meta({'target': 'json'})

    some_bytes = b'["phlipper", "piglet"]'
    assert bytes_fmt.serialize(some_bytes) == some_bytes
    assert json_fmt.deserialize(some_bytes) == ['phlipper', 'piglet']


def test_formats_match():
    bytes_fmt = FormatRegistry.match('bytes')
    json_fmt = FormatRegistry.match('json')

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
        assert FormatRegistry.deserialize(FormatRegistry.serialize(obj, meta), meta) == obj

    df = pd.DataFrame([[1, 2], [3, 4]])
    meta = {}
    assert df.equals(FormatRegistry.deserialize(FormatRegistry.serialize(df, meta), meta))


def test_formats_csv_read():
    csv_file = pathlib.Path(__file__).parent / 'data' / 'csv.csv'

    meta = {'format': {'name': 'csv'}}
    expected_bytes = b'a,b,c,d\n1,2,3,4\n5,6,7,8\n'
    expected_df = FormatRegistry.deserialize(expected_bytes, meta)
    df = FormatRegistry.deserialize(csv_file.read_bytes(), meta)

    assert df.equals(expected_df)
    assert expected_bytes == FormatRegistry.serialize(df, meta)