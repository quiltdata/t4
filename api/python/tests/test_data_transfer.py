#! /usr/bin/python
# -*- coding: utf-8 -*-

""" Testing for data_transfer.py """

### Python imports
# Backports
try: import pathlib2 as pathlib
except ImportError: import pathlib

### Project imports
from t4.data_transfer import TargetType, deserialize_obj

### Code
def test_buggy_parquet():
    """
    Test that T4 avoids crashing on bad Pandas metadata from
    old pyarrow libaries.
    """
    path = pathlib.Path(__file__).parents[0]
    with open(path / 'buggy_parquet.parquet', 'rb') as bad_parq:
        # Make sure this doesn't crash.
        deserialize_obj(bad_parq.read(), TargetType.PYARROW)
