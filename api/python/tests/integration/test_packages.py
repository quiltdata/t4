import botocore
import filecmp
import jsonlines
import os
import pytest

import t4 as he
from t4 import util
from t4 import Package, PhysicalKeyType

from mock import patch

LOCAL_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 'local_manifest.jsonl')
REMOTE_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 't4_manifest.jsonl')

def mock_make_api_call(self, operation_name, kwarg):
    """ Mock boto3's AWS API Calls for testing. """
    if operation_name == 'GetObject':
        parsed_response = {'Body': {'foo'}}
        return parsed_response

class TestPackages():
    """ Integration tests for T4 Packages. """

    def test_read_manifest(self, tmpdir):
        """ Verify reading serialized manifest from disk. """
        pkg = Package.load(open(LOCAL_MANIFEST))


        with pytest.raises(NotImplementedError):
            pkg.get('foo')

        out_path = os.path.join(tmpdir, 'new_manifest.jsonl')
        pkg.dump(open(out_path, "w"))
        
        # Insepct the jsonl to verify everything is maintained, i.e.
        # that load/dump results in an equivalent set.
        original_set = list(jsonlines.Reader(open(LOCAL_MANIFEST)))
        written_set = list(jsonlines.Reader(open(out_path)))
        assert len(original_set) == len(written_set)
        assert sorted(original_set, key=lambda k: k.get('logical_key','manifest')) \
            == sorted(written_set, key=lambda k: k.get('logical_key','manifest'))

    def test_materialize_from_remote(self, tmpdir):
        """ Verify loading data and mainfest transforms from S3. """
        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
            pkg = Package.load(open(REMOTE_MANIFEST))
            assert pkg._data['foo'].physical_keys[0]['type'] == PhysicalKeyType.S3.name
            
            with pytest.raises(NotImplementedError):
                mat_pkg = pkg.materialize(open(REMOTE_MANIFEST))
                assert mat_pkg._data['foo'].physical_keys[0]['type'] == PhysicalKeyType.LOCAL.name

    def test_load_into_t4(self):
        """ Verify loading local manifest and data into S3. """
        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call) as mock:
            pkg = Package.load(open(LOCAL_MANIFEST))

            with pytest.raises(NotImplementedError):
                pkg.materialize(open(REMOTE_MANIFEST))
