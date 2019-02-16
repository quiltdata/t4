"""Implementation of the Python Quilt T4 data package loader."""

from importlib.machinery import ModuleSpec
from t4.util import BASE_PATH
from t4 import list_packages, Package


MODULE_PATH = [BASE_PATH / '.quilt']


class DataPackageLoader:
    """
    Data package module loader. Executes package import code and adds the package to the
    module cache.
    """

    @classmethod
    def create_module(cls, spec):
        """
        Module creator. Returning None causes Python to use the default module creator.
        """
        return None

    @classmethod
    def exec_module(cls, module):
        """
        Module executor.
        """
        name_parts = module.__name__.split('.')

        if module.__name__ == 't4.data':
            # __path__ must be set even if the package is virtual. Since __path__ will be
            # scanned by all other finders preceding this one in sys.meta_path order, make sure
            # it points to someplace lacking importable objects
            module.__path__ = MODULE_PATH
            return module

        elif len(name_parts) == 3:  # e.g. module.__name__ == t4.data.foo
            namespace = name_parts[2]

            # we do not know the name the user will ask for, so populate all valid names
            for pkg in list_packages():
                pkg_user, pkg_name = pkg.split('/')
                if pkg_user == namespace:
                    module.__dict__.update({pkg_name: Package.browse(pkg)})

            module.__path__ = MODULE_PATH
            return module

        else:
            # an implementation for subpackage imports exists, but this has significant
            # consistency issues. For now let's avoid, but you can see the full code at
            # https://github.com/ResidentMario/package-autorelaod/blob/master/loader.py
            raise NotImplementedError


class DataPackageFinder:
    """
    Data package module loader finder. This class sits on `sys.meta_path` and returns the
    loader it knows for a given path, if it knows a compatible loader.
    """

    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        """
        This functions is what gets executed by the loader.
        """
        return ModuleSpec(fullname, DataPackageLoader()) if 't4' in fullname else None
