""" Testing for data_transfer.py """

### Python imports

# Backports
try: import pathlib2 as pathlib
except ImportError: import pathlib

try: import unittest.mock as mock
except ImportError: import mock


### Project imports
from t4 import data_transfer
from t4.data_transfer import TargetType, deserialize_obj


### Third-party imports
import pandas as pd
import pytest


### Code
def test_buggy_parquet():
    """
    Test that T4 avoids crashing on bad Pandas metadata from
    old pyarrow libaries.
    """
    path = pathlib.Path(__file__).parent
    with open(path / 'data' / 'buggy_parquet.parquet', 'rb') as bad_parq:
        # Make sure this doesn't crash.
        deserialize_obj(bad_parq.read(), TargetType.PYARROW)


def test_select():
    chunks = [
        b'{"foo": ',
        b'9, "b',
        b'ar": 3',
        b'}\n{"foo"',
        b': 9, "bar": 1}\n{"foo": 6, "bar": 9}\n{"foo":',
        b' 1, "bar": 7}\n{"foo":',
        b' 6, "bar": 1}\n{"foo": 6, "bar": 6}',
        b'\n{"foo": 9, "bar": 6}',
        b'\n{"foo": 6, "bar": 4}\n',
        b'{"foo": 2, "bar": 0}',
        b'\n{"foo": 2, "bar": 0}\n',
        ]
    records = [{'Records': {'Payload': chunk}} for chunk in chunks]
    # noinspection PyTypeChecker
    records.append({'Stats': {
        'BytesScanned': 100,
        'BytesProcessed': 100,
        'BytesReturned': 210,
        }})
    records.append({'End': {}})

    expected_result = pd.DataFrame.from_records([
        {'foo': 9, 'bar': 3},
        {'foo': 9, 'bar': 1},
        {'foo': 6, 'bar': 9},
        {'foo': 1, 'bar': 7},
        {'foo': 6, 'bar': 1},
        {'foo': 6, 'bar': 6},
        {'foo': 9, 'bar': 6},
        {'foo': 6, 'bar': 4},
        {'foo': 2, 'bar': 0},
        {'foo': 2, 'bar': 0},
        ])

    # test normal use from extension
    expected_args = {
        'Bucket': 'foo',
        'Key': 'bar/baz.json',
        'Expression': 'select * from S3Object',
        'ExpressionType': 'SQL',
        'InputSerialization': {
            'CompressionType': 'NONE',
            'JSON': {'Type': 'DOCUMENT'}
            },
        'OutputSerialization': {'JSON': {}},
        }
    boto_return_val = {'Payload': iter(records)}
    patched_s3 = mock.patch.object(
        data_transfer.s3_client,
        'select_object_content',
        return_value=boto_return_val,
        autospec=True,
    )
    with patched_s3 as patched:
        result = data_transfer.select('s3://foo/bar/baz.json', 'select * from S3Object')

        patched.assert_called_once_with(**expected_args)
        assert result.equals(expected_result)

    # test no format specified
    patched_s3 = mock.patch.object(
        data_transfer.s3_client,
        'select_object_content',
        autospec=True,
    )
    with patched_s3:
        # No format determined.
        with pytest.raises(data_transfer.QuiltException):
            result = data_transfer.select('s3://foo/bar/baz', 'select * from S3Object')

    # test format-specified in metadata
    expected_args = {
        'Bucket': 'foo',
        'Key': 'bar/baz',
        'Expression': 'select * from S3Object',
        'ExpressionType': 'SQL',
        'InputSerialization': {
            'CompressionType': 'NONE',
            'JSON': {'Type': 'DOCUMENT'}
        },
        'OutputSerialization': {'JSON': {}},
    }

    boto_return_val = {'Payload': iter(records)}
    patched_s3 = mock.patch.object(
        data_transfer.s3_client,
        'select_object_content',
        return_value=boto_return_val,
        autospec=True,
    )
    with patched_s3 as patched:
        result = data_transfer.select('s3://foo/bar/baz', 'select * from S3Object', meta={'target': 'json'})
        assert result.equals(expected_result)
        patched.assert_called_once_with(**expected_args)

    # test compression is specified
    expected_args = {
        'Bucket': 'foo',
        'Key': 'bar/baz.json.gz',
        'Expression': 'select * from S3Object',
        'ExpressionType': 'SQL',
        'InputSerialization': {
            'CompressionType': 'GZIP',
            'JSON': {'Type': 'DOCUMENT'}
            },
        'OutputSerialization': {'JSON': {}},
        }
    boto_return_val = {'Payload': iter(records)}
    patched_s3 = mock.patch.object(
        data_transfer.s3_client,
        'select_object_content',
        return_value=boto_return_val,
        autospec=True,
    )
    with patched_s3 as patched:
        # result ignored -- returned data isn't compressed, and this has already been tested.
        data_transfer.select('s3://foo/bar/baz.json.gz', 'select * from S3Object')
        patched.assert_called_once_with(**expected_args)
