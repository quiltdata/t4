""" Integration tests for T4 Packages. """
import jsonlines
import os
import pytest

from t4 import Package, PhysicalKeyType

from mock import patch

LOCAL_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 'local_manifest.jsonl')
REMOTE_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 't4_manifest.jsonl')

def mock_make_api_call(operation_name):
    """ Mock boto3's AWS API Calls for testing. """
    if operation_name == 'GetObject':
        parsed_response = {'Body': {'foo'}}
        return parsed_response
    raise NotImplementedError

def test_read_manifest(tmpdir):
    """ Verify reading serialized manifest from disk. """
    with open(LOCAL_MANIFEST) as fd:
        pkg = Package.load(fd)

    with pytest.raises(NotImplementedError):
        pkg.get('foo')

    out_path = os.path.join(tmpdir, 'new_manifest.jsonl')
    with open(out_path, "w") as fd:
        pkg.dump(fd)
    
    # Insepct the jsonl to verify everything is maintained, i.e.
    # that load/dump results in an equivalent set.
    # todo: Use load/dump once __eq__ implemented.
    original_set = list(jsonlines.Reader(open(LOCAL_MANIFEST)))
    written_set = list(jsonlines.Reader(open(out_path)))
    assert len(original_set) == len(written_set)
    assert sorted(original_set, key=lambda k: k.get('logical_key','manifest')) \
        == sorted(written_set, key=lambda k: k.get('logical_key','manifest'))

def test_materialize_from_remote():
    """ Verify loading data and mainfest transforms from S3. """
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        pkg = Package.load(open(REMOTE_MANIFEST))
        assert PhysicalKeyType.S3.name \
            == pkg._data['foo'].physical_keys[0]['type'] # pylint: disable=W0212
        
        with pytest.raises(NotImplementedError):
            mat_pkg = pkg.materialize(open(REMOTE_MANIFEST))
            assert PhysicalKeyType.LOCAL.name \
                == mat_pkg._data['foo'].physical_keys[0]['type'] # pylint: disable=W0212

def test_load_into_t4():
    """ Verify loading local manifest and data into S3. """
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        pkg = Package.load(open(LOCAL_MANIFEST))

        with pytest.raises(NotImplementedError):
            pkg.materialize(open(REMOTE_MANIFEST))
