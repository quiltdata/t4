""" Integration tests for T4 Packages. """
import appdirs
import io
import jsonlines
import os
import pathlib
import pytest
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

from mock import patch
from pathlib import Path

import t4
from t4 import Package
from t4.packages import get_local_package_registry
from t4.util import QuiltException, APP_NAME, APP_AUTHOR, BASE_DIR, BASE_PATH, parse_file_url

LOCAL_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 'local_manifest.jsonl')
REMOTE_MANIFEST = os.path.join(os.path.dirname(__file__), 'data', 't4_manifest.jsonl')

def mock_make_api_call(self, operation_name, kwarg):
    """ Mock boto3's AWS API Calls for testing. """
    if operation_name == 'GetObject':
        parsed_response = {'Body': {'foo'}}
        return parsed_response
    if operation_name == 'ListObjectsV2':
        parsed_response = {'CommonPrefixes': ['foo']}
        return parsed_response
    if operation_name == 'HeadObject':
        # TODO: mock this somehow
        parsed_response = {
            'Metadata': {},
            'ContentLength': 0
        }
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
    top_hash = new_pkg.build("Quilt/Test")

    # Verify manifest is registered by hash.
    out_path = Path(BASE_PATH, "packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert test_file.resolve().as_uri() \
            == pkg._data['foo'].physical_keys[0] # pylint: disable=W0212

    # Verify latest points to the new location.
    named_pointer_path = Path(BASE_PATH, "named_packages", "Quilt", "Test", "latest")
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

def no_op_mock(*args, **kwargs):
    pass

def test_materialize_from_remote(tmpdir):
    """ Verify loading data and mainfest transforms from S3. """
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with open(REMOTE_MANIFEST) as fd:
            pkg = Package.load(fd)
            with patch('t4.data_transfer._download_single_file', new=no_op_mock), \
                 patch('t4.data_transfer._download_dir', new=no_op_mock), \
                 patch('t4.Package.build', new=no_op_mock):
                mat_pkg = pkg.push(os.path.join(tmpdir, 'pkg'), name='Quilt/test_pkg_name')

def test_package_constructor_from_registry():
    """ Verify loading manifest locally and from s3 """
    with patch('t4.Package._from_path') as pkgmock:
        registry = BASE_PATH.as_uri()
        pkg = Package()
        pkgmock.return_value = pkg
        pkghash = pkg.top_hash()

        # local load
        pkg = Package(pkg_hash=pkghash)
        assert registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()

        pkg = Package('Quilt/nice-name', pkg_hash=pkghash)
        assert registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()

        with patch('t4.packages.open') as open_mock:
            open_mock.return_value = io.BytesIO(pkghash.encode('utf-8'))
            pkg = Package('Quilt/nice-name')
            assert parse_file_url(urlparse(registry + '/named_packages/Quilt/nice-name/latest')) \
                    == open_mock.call_args_list[0][0][0]

        assert registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]
        pkgmock.reset_mock()

        remote_registry = t4.packages.get_package_registry('s3://asdf/')
        # remote load
        pkg = Package('Quilt/nice-name', registry=remote_registry, pkg_hash=pkghash)
        assert remote_registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]
        pkgmock.reset_mock()
        pkg = Package(pkg_hash=pkghash, registry=remote_registry)
        assert remote_registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()
        with patch('t4.packages.download_bytes') as dl_mock:
            dl_mock.return_value = (pkghash.encode('utf-8'), None)
            pkg = Package('Quilt/nice-name', registry=remote_registry)
        assert remote_registry + '/packages/{}'.format(pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

def test_load_into_t4(tmpdir):
    """ Verify loading local manifest and data into S3. """
    with patch('t4.packages.copy_file') as mock:
        new_pkg = Package()
        # Create a dummy file to add to the package.
        test_file = os.path.join(tmpdir, 'bar')
        with open(test_file, 'w') as fd:
            fd.write(test_file)
        new_pkg = new_pkg.set('foo', test_file)
        new_pkg.push('s3://my_test_bucket/', name='Quilt/package_name')

        # Get the second argument (destination) from the non-keyword args list
        dest_args = [x[0][1] for x in mock.call_args_list]

        # Manifest copied
        assert 's3://my_test_bucket/.quilt/packages/' + new_pkg.top_hash() in dest_args
        assert 's3://my_test_bucket/.quilt/named_packages/Quilt/package_name/latest' in dest_args

        # Data copied
        assert 's3://my_test_bucket/Quilt/package_name/foo' in dest_args

def test_local_push(tmpdir):
    """ Verify loading local manifest and data into S3. """
    with patch('t4.packages.copy_file') as mock:
        new_pkg = Package()
        test_file = os.path.join(tmpdir, 'bar')
        with open(test_file, 'w') as fd:
            fd.write(test_file)
        new_pkg = new_pkg.set('foo', test_file)
        new_pkg.push(os.path.join(tmpdir, 'package_contents'), name='Quilt/package')

        # Get the second argument (destination) from the non-keyword args list
        dest_args = [x[0][1] for x in mock.call_args_list]

        # Manifest copied
        assert get_local_package_registry().as_uri() + '/packages/' + \
                new_pkg.top_hash() in dest_args
        assert get_local_package_registry().as_uri() + \
                '/named_packages/Quilt/package/latest' in dest_args

        # Data copied
        assert pathlib.Path(os.path.join(tmpdir, 'package_contents/Quilt/package/foo')).as_uri() \
            in dest_args

def test_package_get(tmpdir):
    """ Verify loading data from a local file. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'))
    )

    assert pkg.get('foo') == ('123\n', 'blah')

    with pytest.raises(QuiltException):
        pkg.get('bar')

def test_capture(tmpdir):
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


def test_updates(tmpdir):
    """ Verify building a package from a directory. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
            {'target': 'unicode', 'user_meta': 'blah'})
    )
    assert pkg.get('foo') == ('123\n', 'blah')
    assert pkg.get('bar') == ('123\n', 'blah')

    # Build a dummy file to add to the map.
    with open('bar.txt', "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)
    pkg = pkg.update({'bar': 'bar.txt'})
    assert test_file.resolve().as_uri() \
        == pkg._data['bar'].physical_keys[0] # pylint: disable=W0212

    # Build a dummy file to add to the map with a prefix.
    with open('baz.txt', "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)
    pkg = pkg.update({'baz': 'baz.txt'}, prefix='prefix/')
    assert test_file.resolve().as_uri() \
        == pkg._data['prefix/baz'].physical_keys[0] # pylint: disable=W0212


    assert pkg.get('foo') == ('123\n', 'blah')

def test_list_local_packages(tmpdir):
    """Verify that list returns packages in the appdirs directory."""
    temp_local_registry = Path(os.path.join(tmpdir, 'test_registry'))
    with patch('t4.packages.get_local_package_registry', lambda: temp_local_registry):
        # Build a new package into the local registry.
        Package().build("Quilt/Foo")
        Package().build("Quilt/Bar")
        Package().build("Quilt/Test")

        # Verify packages are returned.
        pkgs = t4.list_packages()
        assert len(pkgs) == 3
        assert "Quilt/Foo" in pkgs
        assert "Quilt/Bar" in pkgs

        # Test unnamed packages are not added.
        Package().build()
        pkgs = t4.list_packages()
        assert len(pkgs) == 3

        # Verify manifest is registered by hash when local path given
        pkgs = t4.list_packages("/")
        assert "Quilt/Foo" in pkgs
        assert "Quilt/Bar" in pkgs

def test_tophash_changes():
    with NamedTemporaryFile() as test_file:
        test_file.write('asdf'.encode('utf-8'))
        pkg = Package()
        th1 = pkg.top_hash()
        pkg.set('asdf', test_file.name)
        th2 = pkg.top_hash()
        assert th1 != th2

        test_file.write('jkl'.encode('utf-8'))
        pkg.set('jkl', test_file.name)
        th3 = pkg.top_hash()
        assert th1 != th3
        assert th2 != th3

        pkg.delete('jkl')
        th4 = pkg.top_hash()
        assert th2 == th4
        
        pkg.delete('asdf')
        assert th1 == pkg.top_hash()

def test_keys():
    pkg = Package()
    assert pkg.keys() == []

    pkg.set('asdf', LOCAL_MANIFEST)
    assert pkg.keys() == ['asdf']

    pkg.set('jkl;', REMOTE_MANIFEST)
    assert set(pkg.keys()) == set(['asdf', 'jkl;'])

    pkg.delete('asdf')
    assert pkg.keys() == ['jkl;']

def test_list_remote_packages():
    with patch('t4.api.list_objects',
               return_value=([{'Prefix': 'foo'},{'Prefix': 'bar'}],[])) as mock:
        pkgs = t4.list_packages('s3://my_test_bucket/')
        assert mock.call_args_list[0][0][0] == \
            'my_test_bucket/.quilt/named_packages/'

    assert True


def test_validate_package_name():
    Package.validate_package_name("a/b")
    Package.validate_package_name("21312/bes")
    with pytest.raises(QuiltException):
        Package.validate_package_name("b")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/b/")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/b/c")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/")
    with pytest.raises(QuiltException):
        Package.validate_package_name("/b")
    with pytest.raises(QuiltException):
        Package.validate_package_name("b")

