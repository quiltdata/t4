""" Integration tests for T4 Packages. """
import appdirs
import jsonlines
import os
import pytest

from t4 import Package, PhysicalKeyType
from t4.util import HeliumException

from mock import patch

LOCAL_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 'local_manifest.jsonl')
REMOTE_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 't4_manifest.jsonl')

def mock_make_api_call(operation_name):
    """ Mock boto3's AWS API Calls for testing. """
    if operation_name == 'GetObject':
        parsed_response = {'Body': {'foo'}}
        return parsed_response
    raise NotImplementedError

def test_build(tmpdir):
    """Verify that build dumps the manifest to appdirs directory."""
    new_pkg = Package()

    # Create a dummy file to add to the package.
    test_file = os.path.join(tmpdir, 'bar')
    with open(test_file, "w") as fd:    
        fd.write(test_file)

    # Build a new package into the local registry.
    new_pkg = new_pkg.set('foo', test_file)
    top_hash = new_pkg.build("Test")

    # Verify manifest is registered by hash.
    out_path = os.path.join(appdirs.user_data_dir("quilt"), "packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert "file://" + test_file \
            == pkg._data['foo'].physical_keys[0]['path'] # pylint: disable=W0212

    # Verify latest points to the new location.
    named_pointer_path = os.path.join(
        appdirs.user_data_dir("quilt"),
        "named_packages",
        "Test",
        "latest")
    with open(named_pointer_path) as fd:
        assert fd.read().replace('\n', '') == top_hash

def test_read_manifest(tmpdir):
    """ Verify reading serialized manifest from disk. """
    with open(LOCAL_MANIFEST) as fd:
        pkg = Package.load(fd)

    out_path = os.path.join(tmpdir, 'new_manifest.jsonl')
    with open(out_path, "w") as fd:
        pkg.dump(fd)
    
    # Insepct the jsonl to verify everything is maintained, i.e.
    # that load/dump results in an equivalent set.
    # todo: Use load/dump once __eq__ implemented.
    with open(LOCAL_MANIFEST) as fd:
        original_set = list(jsonlines.Reader(fd))
    with open(out_path) as fd:
        written_set = list(jsonlines.Reader(fd))
    assert len(original_set) == len(written_set)
    assert sorted(original_set, key=lambda k: k.get('logical_key','manifest')) \
        == sorted(written_set, key=lambda k: k.get('logical_key','manifest'))

def test_materialize_from_remote():
    """ Verify loading data and mainfest transforms from S3. """
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with open(REMOTE_MANIFEST) as fd:   
            pkg = Package.load(fd)
        assert PhysicalKeyType.S3.name \
            == pkg._data['foo'].physical_keys[0]['type'] # pylint: disable=W0212
        
        with pytest.raises(NotImplementedError):
            with open(REMOTE_MANIFEST) as fd:   
                mat_pkg = pkg.materialize(fd)
            assert PhysicalKeyType.LOCAL.name \
                == mat_pkg._data['foo'].physical_keys[0]['type'] # pylint: disable=W0212

def test_load_into_t4():
    """ Verify loading local manifest and data into S3. """
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with open(LOCAL_MANIFEST) as fd:
            pkg = Package.load(fd)

        with pytest.raises(NotImplementedError):
            with open(REMOTE_MANIFEST) as fd:   
                pkg.materialize(fd)

def test_package_get():
    """ Verify loading data from a local file. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'))
    )

    assert pkg.get('foo') == ('123\n', 'blah')

    with pytest.raises(HeliumException):
        pkg.get('bar')
