""" Integration tests for T4 Packages. """
import jsonlines
import os
import pathlib
import pytest

from mock import patch
from pathlib import Path

from t4 import Package
from t4.util import HeliumException, BASE_PATH


LOCAL_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 'local_manifest.jsonl')
REMOTE_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 't4_manifest.jsonl')

def mock_make_api_call(self, operation_name, kwarg):
    """ Mock boto3's AWS API Calls for testing. """
    if operation_name == 'GetObject':
        parsed_response = {'Body': {'foo'}}
        return parsed_response
    raise NotImplementedError(operation_name)

@patch('appdirs.user_data_dir', lambda x,y: os.path.join('test_appdir', x))
def test_build(tmpdir):
    """Verify that build dumps the manifest to appdirs directory."""
    new_pkg = Package()

    # Create a dummy file to add to the package.
    test_file_name = 'bar'
    with open(test_file_name, "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)

    # Build a new package into the local registry.
    new_pkg = new_pkg.set('foo', test_file_name)
    top_hash = new_pkg.build("Test")

    # Verify manifest is registered by hash.
    out_path = Path(BASE_PATH, "packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert test_file.resolve().as_uri() \
            == pkg._data['foo'].physical_keys[0] # pylint: disable=W0212

    # Verify latest points to the new location.
    named_pointer_path = Path(BASE_PATH, "named_packages", "Test", "latest")
    with open(named_pointer_path) as fd:
        assert fd.read().replace('\n', '') == top_hash

    # Test unnamed packages.
    new_pkg = Package()
    new_pkg = new_pkg.set('bar', test_file_name)
    top_hash = new_pkg.build()
    out_path = Path(BASE_PATH, "packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert test_file.resolve().as_uri() \
            == pkg._data['bar'].physical_keys[0] # pylint: disable=W0212


def test_read_manifest(tmpdir):
    """ Verify reading serialized manifest from disk. """
    with open(LOCAL_MANIFEST) as fd:
        pkg = Package.load(fd)

    out_path = os.path.join(tmpdir, 'new_manifest.jsonl')
    with open(out_path, 'w') as fd:
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
        with pytest.raises(NotImplementedError):
            with open(REMOTE_MANIFEST) as fd:   
                mat_pkg = pkg.push('test_pkg_name','/')

def test_load_into_t4(tmpdir):
    """ Verify loading local manifest and data into S3. """
    with patch('t4.packages._copy_file') as mock:
        new_pkg = Package()
        # Create a dummy file to add to the package.
        test_file = os.path.join(tmpdir, 'bar')
        with open(test_file, 'w') as fd:    
            fd.write(test_file)
        new_pkg = new_pkg.set('foo', test_file)
        new_pkg.push('package_name', 's3://my_test_bucket/')

        # Get the second argument (destination) from the non-keyword args list
        dest_args = [x[0][1] for x in mock.call_args_list]

        # Manifest copied
        assert 's3://my_test_bucket/.quilt/packages/' + new_pkg.top_hash()['value'] in dest_args
        assert 's3://my_test_bucket/.quilt/named_packages/package_name/latest' in dest_args

        # Data copied
        assert 's3://my_test_bucket/package_name/foo' in dest_args

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

def test_capture():
    """ Verify building a package from a directory. """
    pkg = Package()
    
    # Create some nested example files that contain their names.
    foodir = pathlib.Path("foo_dir")
    bazdir = pathlib.Path(foodir, "baz_dir")
    bazdir.mkdir(parents=True, exist_ok=True)
    with open('bar', 'w') as fd:
        fd.write(fd.name)
    with open('foo', 'w') as fd:
        fd.write(fd.name)
    with open(bazdir / 'baz', 'w') as fd: 
        fd.write(fd.name)
    with open(foodir / 'bar', 'w') as fd:
        fd.write(fd.name)

    pkg = pkg.capture("")

    assert pathlib.Path('foo').resolve().as_uri() \
        == pkg._data['foo'].physical_keys[0] # pylint: disable=W0212
    assert pathlib.Path('bar').resolve().as_uri() \
        == pkg._data['bar'].physical_keys[0] # pylint: disable=W0212
    assert pathlib.Path(bazdir / 'baz').resolve().as_uri() \
        == pkg._data['foo_dir/baz_dir/baz'].physical_keys[0] # pylint: disable=W0212
    assert pathlib.Path(foodir / 'bar').resolve().as_uri() \
        == pkg._data['foo_dir/bar'].physical_keys[0] # pylint: disable=W0212

    pkg = Package()
    pkg = pkg.capture('foo_dir/baz_dir/')
    # todo nested at capture site or relative to capture path.
    assert pathlib.Path(bazdir / 'baz').resolve().as_uri() \
        == pkg._data['baz'].physical_keys[0] # pylint: disable=W0212

    pkg = Package()
    pkg = pkg.capture('foo_dir/baz_dir/', prefix='my_keys')
    # todo nested at capture site or relative to capture path.
    assert pathlib.Path(bazdir / 'baz').resolve().as_uri() \
        == pkg._data['my_keys/baz'].physical_keys[0] # pylint: disable=W0212
