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



