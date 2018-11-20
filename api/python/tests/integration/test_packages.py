""" Integration tests for T4 Packages. """
import os
import pathlib
from pathlib import Path
import shutil
from urllib.parse import urlparse

import jsonlines
from mock import patch
import pytest

import t4
from t4 import Package
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
    out_path = Path(BASE_PATH, ".quilt/packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert test_file.resolve().as_uri() == pkg['foo'].physical_keys[0]

    # Verify latest points to the new location.
    named_pointer_path = Path(BASE_PATH, ".quilt/named_packages/Quilt/Test/latest")
    with open(named_pointer_path) as fd:
        assert fd.read().replace('\n', '') == top_hash

    # Test unnamed packages.
    new_pkg = Package()
    new_pkg = new_pkg.set('bar', test_file_name)
    top_hash = new_pkg.build()
    out_path = Path(BASE_PATH, ".quilt/packages", top_hash)
    with open(out_path) as fd:
        pkg = Package.load(fd)
        assert test_file.resolve().as_uri() == pkg['bar'].physical_keys[0]


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
            mat_pkg = pkg.push('Quilt/test_pkg_name', tmpdir / 'pkg')

def test_browse_package_from_registry():
    """ Verify loading manifest locally and from s3 """
    with patch('t4.Package._from_path') as pkgmock:
        registry = BASE_PATH.as_uri()
        pkg = Package()
        pkgmock.return_value = pkg
        pkghash = pkg.top_hash()

        # default registry load
        pkg = Package.browse(pkg_hash=pkghash)
        assert '{}/.quilt/packages/{}'.format(registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()

        pkg = Package.browse('Quilt/nice-name', pkg_hash=pkghash)
        assert '{}/.quilt/packages/{}'.format(registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()

        with patch('t4.packages.get_bytes') as dl_mock:
            dl_mock.return_value = (pkghash.encode('utf-8'), None)
            pkg = Package.browse('Quilt/nice-name')
            assert registry + '/.quilt/named_packages/Quilt/nice-name/latest' \
                    == dl_mock.call_args_list[0][0][0]

        assert '{}/.quilt/packages/{}'.format(registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]
        pkgmock.reset_mock()

        remote_registry = 's3://asdf/foo'
        # remote load
        pkg = Package.browse('Quilt/nice-name', registry=remote_registry, pkg_hash=pkghash)
        assert '{}/.quilt/packages/{}'.format(remote_registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]
        pkgmock.reset_mock()
        pkg = Package.browse(pkg_hash=pkghash, registry=remote_registry)
        assert '{}/.quilt/packages/{}'.format(remote_registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

        pkgmock.reset_mock()
        with patch('t4.packages.get_bytes') as dl_mock:
            dl_mock.return_value = (pkghash.encode('utf-8'), None)
            pkg = Package.browse('Quilt/nice-name', registry=remote_registry)
        assert '{}/.quilt/packages/{}'.format(remote_registry, pkghash) \
                in [x[0][0] for x in pkgmock.call_args_list]

def test_package_fetch(tmpdir):
    """ Package.fetch() on nested, relative keys """
    input_dir = os.path.dirname(__file__)
    package_ = Package().set_dir('/', os.path.join(input_dir, 'data', 'nested'))

    out_dir = os.path.join(tmpdir, 'output')
    package_.fetch(out_dir)

    expected = {'one.txt': '1', 'two.txt': '2', 'three.txt': '3'}
    file_count = 0
    for dirpath, _, files in os.walk(out_dir):
        for name in files:
            file_count += 1
            with open(os.path.join(out_dir, dirpath, name)) as file_:
                assert name in expected, 'unexpected file: {}'.format(file_)
                contents = file_.read().strip()
                assert contents == expected[name], \
                    'unexpected contents in {}: {}'.format(name, contents)
    assert file_count == len(expected), \
        'fetch wrote {} files; expected: {}'.format(file_count, expected)

def test_fetch(tmpdir):
    """ Verify fetching a package entry. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
    )

    with open(os.path.join(os.path.dirname(__file__), 'data', 'foo.txt')) as fd:
        assert fd.read().replace('\n', '') == '123'
    # Copy foo.text to bar.txt
    pkg['foo'].fetch(os.path.join(tmpdir, 'data', 'bar.txt'))
    with open(os.path.join(tmpdir, 'data', 'bar.txt')) as fd:
        assert fd.read().replace('\n', '') == '123'

    # Raise an error if you copy to yourself.
    with pytest.raises(shutil.SameFileError):
        pkg['foo'].fetch(os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'))

def test_load_into_t4(tmpdir):
    """ Verify loading local manifest and data into S3. """
    with patch('t4.packages.put_bytes') as bytes_mock, \
         patch('t4.packages.copy_file') as file_mock:
        new_pkg = Package()
        # Create a dummy file to add to the package.
        test_file = os.path.join(tmpdir, 'bar')
        with open(test_file, 'w') as fd:
            fd.write(test_file)
        new_pkg = new_pkg.set('foo', test_file)
        new_pkg.push('Quilt/package_name', 's3://my_test_bucket/')

        # Get the second argument (destination) from the non-keyword args list
        bytes_dest_args = [x[0][1] for x in bytes_mock.call_args_list]
        file_dest_args = [x[0][1] for x in file_mock.call_args_list]

        # Manifest copied
        assert 's3://my_test_bucket/.quilt/packages/' + new_pkg.top_hash() in bytes_dest_args
        assert 's3://my_test_bucket/.quilt/named_packages/Quilt/package_name/latest' in bytes_dest_args

        # Data copied
        assert 's3://my_test_bucket/Quilt/package_name/foo' in file_dest_args

def test_local_push(tmpdir):
    """ Verify loading local manifest and data into S3. """
    with patch('t4.packages.put_bytes') as bytes_mock, \
         patch('t4.packages.copy_file') as file_mock:
        new_pkg = Package()
        test_file = os.path.join(tmpdir, 'bar')
        with open(test_file, 'w') as fd:
            fd.write(test_file)
        new_pkg = new_pkg.set('foo', test_file)
        new_pkg.push('Quilt/package', tmpdir / 'package_contents')

        push_uri = pathlib.Path(tmpdir, 'package_contents').as_uri()

        # Get the second argument (destination) from the non-keyword args list
        bytes_dest_args = [x[0][1] for x in bytes_mock.call_args_list]
        file_dest_args = [x[0][1] for x in file_mock.call_args_list]

        # Manifest copied
        assert push_uri + '/.quilt/packages/' + new_pkg.top_hash() in bytes_dest_args
        assert push_uri + '/.quilt/named_packages/Quilt/package/latest' in bytes_dest_args

        # Data copied
        assert push_uri + '/Quilt/package/foo' in file_dest_args

def test_package_deserialize(tmpdir):
    """ Verify loading data from a local file. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'))
    )
    pkg.build()

    assert pkg['foo'].deserialize() == '123\n'

    with pytest.raises(QuiltException):
        pkg['bar'].deserialize()

def test_set_dir(tmpdir):
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

    pkg = pkg.set_dir("/", ".")

    assert pathlib.Path('foo').resolve().as_uri() == pkg['foo'].physical_keys[0]
    assert pathlib.Path('bar').resolve().as_uri() == pkg['bar'].physical_keys[0]
    assert (bazdir / 'baz').resolve().as_uri() == pkg['foo_dir/baz_dir/baz'].physical_keys[0]
    assert (foodir / 'bar').resolve().as_uri() == pkg['foo_dir/bar'].physical_keys[0]

    pkg = Package()
    pkg = pkg.set_dir('/','foo_dir/baz_dir/')
    # todo nested at set_dir site or relative to set_dir path.
    assert (bazdir / 'baz').resolve().as_uri() == pkg['baz'].physical_keys[0]

    pkg = Package()
    pkg = pkg.set_dir('my_keys', 'foo_dir/baz_dir/')
    # todo nested at set_dir site or relative to set_dir path.
    assert (bazdir / 'baz').resolve().as_uri() == pkg['my_keys/baz'].physical_keys[0]


def test_updates(tmpdir):
    """ Verify building a package from a directory. """
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
            {'target': 'unicode', 'user_meta': 'blah'})
    )
    pkg.build()

    assert pkg['foo']() == '123\n'
    assert pkg['bar']() == '123\n'

    # Build a dummy file to add to the map.
    with open('bar.txt', "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)
    pkg = pkg.update({'bar': 'bar.txt'})
    assert test_file.resolve().as_uri() == pkg['bar'].physical_keys[0]

    assert pkg['foo']() == '123\n'

    # Build a dummy file to add to the map with a prefix.
    with open('baz.txt', "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)
    pkg = pkg.update({'baz': 'baz.txt'}, prefix='prefix/')
    assert test_file.resolve().as_uri() == pkg['prefix/baz'].physical_keys[0]

    assert pkg['foo']() == '123\n'


def test_package_entry_meta():
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
            {'target': 'unicode', 'user_meta': {'value': 'blah'}})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
            {'target': 'unicode', 'user_meta': {'value': 'blah2'}})
    )

    assert pkg['foo'].get_user_meta() == {'value': 'blah'}
    assert pkg['bar'].get_user_meta() == {'value': 'blah2'}

    assert pkg['foo'].meta == {'target': 'unicode', 'user_meta': {'value': 'blah'}}
    assert pkg['bar'].meta == {'target': 'unicode', 'user_meta': {'value': 'blah2'}}

    pkg['foo'].set_user_meta({'value': 'other value'})
    assert pkg['foo'].get_user_meta() == {'value': 'other value'}
    assert pkg['foo'].meta == {'target': 'unicode', 'user_meta': {'value': 'other value'}}


def test_list_local_packages(tmpdir):
    """Verify that list returns packages in the appdirs directory."""
    temp_local_registry = Path(os.path.join(tmpdir, 'test_registry')).as_uri()
    with patch('t4.packages.get_package_registry', lambda path: temp_local_registry), \
         patch('t4.api.get_package_registry', lambda path: temp_local_registry):
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

def test_set_package_entry(tmpdir):
    """ Set the physical key for a PackageEntry"""
    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
        .set('bar', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
            {'target': 'unicode', 'user_meta': 'blah'})
    )

    # Build a dummy file to add to the map.
    with open('bar.txt', "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)
    pkg['bar'].set('bar.txt')

    assert test_file.resolve().as_uri() == pkg['bar'].physical_keys[0]

def test_tophash_changes(tmpdir):
    test_file = tmpdir / 'test.txt'
    test_file.write_text('asdf', 'utf-8')

    pkg = Package()
    th1 = pkg.top_hash()
    pkg.set('asdf', test_file)
    pkg.build()
    th2 = pkg.top_hash()
    assert th1 != th2

    test_file.write_text('jkl', 'utf-8')
    pkg.set('jkl', test_file)
    pkg.build()
    th3 = pkg.top_hash()
    assert th1 != th3
    assert th2 != th3

    pkg.delete('jkl')
    th4 = pkg.top_hash()
    assert th2 == th4

def test_keys():
    pkg = Package()
    assert not pkg.keys()

    pkg.set('asdf', LOCAL_MANIFEST)
    assert set(pkg.keys()) == {'asdf'}

    pkg.set('jkl;', REMOTE_MANIFEST)
    assert set(pkg.keys()) == {'asdf', 'jkl;'}

    pkg.delete('asdf')
    assert set(pkg.keys()) == {'jkl;'}


def test_iter():
    pkg = Package()
    assert not pkg

    pkg.set('asdf', LOCAL_MANIFEST)
    assert list(pkg) == ['asdf']

    pkg.set('jkl;', REMOTE_MANIFEST)
    assert set(pkg) == {'asdf', 'jkl;'}

def test_invalid_set_key(tmpdir):
    """Verify an exception when setting a key with a path object."""
    pkg = Package()
    with pytest.raises(TypeError):
        pkg.set('asdf/jkl', 123)

def test_brackets():
    pkg = Package()
    pkg.set('asdf/jkl', LOCAL_MANIFEST)
    pkg.set('asdf/qwer', LOCAL_MANIFEST)
    pkg.set('qwer/asdf', LOCAL_MANIFEST)
    assert set(pkg.keys()) == {'asdf', 'qwer'}

    pkg2 = pkg['asdf']
    assert set(pkg2.keys()) == {'jkl', 'qwer'}

    assert pkg['asdf']['qwer'].get() == pathlib.Path(LOCAL_MANIFEST).as_uri()

    assert pkg['asdf']['qwer'] == pkg['asdf/qwer'] == pkg[('asdf', 'qwer')]
    assert pkg[[]] == pkg

    pkg = (
        Package()
        .set('foo', os.path.join(os.path.dirname(__file__), 'data', 'foo.txt'),
             {'target': 'unicode', 'user_meta': 'blah'})
    )

    pkg.build()

    assert pkg['foo'].deserialize() == '123\n'
    assert pkg['foo']() == '123\n'

    with pytest.raises(KeyError):
        pkg['baz']

    with pytest.raises(TypeError):
        pkg[b'asdf']

    with pytest.raises(TypeError):
        pkg[0]

def test_list_remote_packages():
    with patch('t4.api.list_objects',
               return_value=([{'Prefix': 'foo'},{'Prefix': 'bar'}],[])) as mock:
        pkgs = t4.list_packages('s3://my_test_bucket/')
        assert mock.call_args_list[0][0] == ('my_test_bucket', '.quilt/named_packages/')

    assert True


def test_validate_package_name():
    Package.validate_package_name("a/b")
    Package.validate_package_name("21312/bes")
    with pytest.raises(QuiltException):
        Package.validate_package_name("b")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/b/")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a\\/b")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/b/c")
    with pytest.raises(QuiltException):
        Package.validate_package_name("a/")
    with pytest.raises(QuiltException):
        Package.validate_package_name("/b")
    with pytest.raises(QuiltException):
        Package.validate_package_name("b")

def test_diff():
    new_pkg = Package()

    # Create a dummy file to add to the package.
    test_file_name = 'bar'
    with open(test_file_name, "w") as fd:
        fd.write('test_file_content_string')
        test_file = Path(fd.name)

    # Build a new package into the local registry.
    new_pkg = new_pkg.set('foo', test_file_name)
    top_hash = new_pkg.build("Quilt/Test")

    p1 = Package.browse('Quilt/Test')
    p2 = Package.browse('Quilt/Test')
    assert p1.diff(p2) == ([], [], [])


def test_dir_meta(tmpdir):
    test_meta = {'test': 'meta'}
    pkg = Package()
    pkg.set('asdf/jkl', LOCAL_MANIFEST)
    pkg.set('asdf/qwer', LOCAL_MANIFEST)
    pkg.set('qwer/asdf', LOCAL_MANIFEST)
    pkg.set('qwer/as/df', LOCAL_MANIFEST)
    pkg.build()
    assert pkg['asdf'].get_meta() == {}
    assert pkg.get_meta() == {}
    assert pkg['qwer']['as'].get_meta() == {}
    pkg['asdf'].set_meta(test_meta)
    assert pkg['asdf'].get_meta() == test_meta
    pkg['qwer']['as'].set_meta(test_meta)
    assert pkg['qwer']['as'].get_meta() == test_meta
    pkg.set_meta(test_meta)
    assert pkg.get_meta() == test_meta
    dump_path = os.path.join(tmpdir, 'test_meta')
    with open(dump_path, 'w') as f:
        pkg.dump(f)
    with open(dump_path) as f:
        pkg2 = Package.load(f)
    assert pkg2['asdf'].get_meta() == test_meta
    assert pkg2['qwer']['as'].get_meta() == test_meta
    assert pkg2.get_meta() == test_meta
    
def test_top_hash_stable():
    """Ensure that top_hash() never changes for a given manifest"""

    registry = Path(__file__).parent / 'data'
    pkg_hash = '20de5433549a4db332a11d8d64b934a82bdea8f144b4aecd901e7d4134f8e733'

    pkg = Package.browse(registry=registry, pkg_hash=pkg_hash)

    assert pkg.top_hash() == pkg_hash, \
           "Unexpected top_hash for {}/.quilt/packages/{}".format(registry, pkg_hash)

def test_commit_message_on_push(tmpdir):
    """ Verify commit messages populate correctly on push."""
    with patch('botocore.client.BaseClient._make_api_call', new=mock_make_api_call):
        with open(REMOTE_MANIFEST) as fd:
            pkg = Package.load(fd)
        with patch('t4.data_transfer._download_single_file', new=no_op_mock), \
                patch('t4.data_transfer._download_dir', new=no_op_mock), \
                patch('t4.Package.build', new=no_op_mock):
            pkg.push('Quilt/test_pkg_name', tmpdir / 'pkg', message='test_message')
            assert pkg._meta['message'] == 'test_message'

            # ensure messages are strings
            with pytest.raises(ValueError):
                pkg.push('Quilt/test_pkg_name', tmpdir / 'pkg', message={})

def test_overwrite_dir_fails():
    with pytest.raises(QuiltException):
        pkg = Package()
        pkg.set('asdf/jkl', LOCAL_MANIFEST)
        pkg.set('asdf', LOCAL_MANIFEST)

def test_overwrite_entry_fails():
    with pytest.raises(QuiltException):
        pkg = Package()
        pkg.set('asdf', LOCAL_MANIFEST)
        pkg.set('asdf/jkl', LOCAL_MANIFEST)

def test_siblings_succeed():
    pkg = Package()
    pkg.set('as/df', LOCAL_MANIFEST)
    pkg.set('as/qw', LOCAL_MANIFEST)
