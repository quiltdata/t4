
### stdlib and backports
try:
    import unittest.mock as mock
except ImportError:
    import mock

try:
    from pathlib2 import Path
except ImportError:
    from pathlib import Path

import os

# third party imports
import pytest


# Module Vars / Constants
class _Vars():
    temp_dir = None
    base_dir = None
    base_path = None
    config_path = None

vars = _Vars()

# scope: function, class, module, or session
# autouse: boolean.  Apply to all instances of the given scope.
@pytest.fixture(scope='session', autouse=True)
def each_session(request, tmpdir_factory):
    print("\nSetup session..")

    if vars.temp_dir is None:
        # returns a.. ..py.path.local?  non-standard path library, inherits str.
        vars.temp_dir = tmpdir_factory.mktemp('test_home')
    vars.base_dir = vars.temp_dir.mkdir('helium_base')
    vars.base_path = Path(vars.base_dir)
    vars.config_path = vars.base_path / 'config.yml'

    mockers = [
        mock.patch('helium.util.BASE_DIR', vars.base_dir),
        mock.patch('helium.util.BASE_PATH', vars.base_path),
        mock.patch('helium.util.CONFIG_PATH', vars.config_path),
        mock.patch('helium.api.CONFIG_PATH', vars.config_path),
        ]
    for mocker in mockers:
        mocker.start()

    def teardown():  # can be named whatever
        print("\nTeardown session..")
        # Not super-necessary, as this is session-scoped, but let's clean up anyways..
        for mocker in mockers:
            mocker.stop()

    request.addfinalizer(teardown)


@pytest.fixture(scope='function', autouse=True)
def set_temporary_working_dir(request, tmpdir):
    print("Setting tempdir to {}".format(tmpdir))
    orig_dir = os.getcwd()
    os.chdir(tmpdir)

    def teardown():  # can be named whatever
        print("Unsetting tempdir..")
        os.chdir(orig_dir)

    request.addfinalizer(teardown)
