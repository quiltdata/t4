import botocore
import filecmp
import os
import pytest

import t4 as he
from t4 import util
from t4 import Package

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
        pkg = Package.load(LOCAL_MANIFEST)
        assert pkg.get('foo')
        out_path = os.path.join(tmpdir, 'new_manifest.jsonl')
        pkg.dump(out_path)
        assert filecmp.cmp(LOCAL_MANIFEST, out_path)

    def test_materialize_from_remote(self, tmpdir):
        """ Verify loading data and mainfest transforms from S3. """
        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
            pkg = Package.load(REMOTE_MANIFEST)
            assert pkg._data['foo'].physical_keys[0] is Package.PhysicalKeyType.S3_CONSTANT
            
            mat_pkg = pkg.materialize(REMOTE_MANIFEST)
            assert mat_pkg._data['foo'].physical_keys[0] is Package.PhysicalKeyType.FILE_CONSTANT

    def test_load_into_t4(self):
        """ Verify loading local manifest and data into S3. """
        with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call) as mock:
            pkg = Package.load(LOCAL_MANIFEST)
            pkg.materialize(REMOTE_MANIFEST)

            assert mock.called

            he.config()
            he.pus
