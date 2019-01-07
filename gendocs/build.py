#! python3

import sys
import subprocess
import pkg_resources
try:
    from pip._internal import main as pipmain
except ImportError:
    from pip import main as pipmain


# To push out and use a new version of pydocmd to people generating docs,
# increment this here and in the quilt pydocmd repo (setup.py and __init__.py)
EXPECTED_VERSION_SUFFIX = '-quilt1'


if __name__ == "__main__":
    try:
        pydocmd_dist = pkg_resources.get_distribution('pydoc-markdown')  # install name, not module name
        version = pydocmd_dist.version
    except pkg_resources.DistributionNotFound:
        version = ''

    if not version.endswith(EXPECTED_VERSION_SUFFIX):
        valid_input = ['y', 'n', 'yes', 'no']
        response = ''

        while response not in valid_input:
            print("\nUsing {!r}:".format(sys.executable))
            if version:
                print("This will uninstall the existing version of pydoc-markdown ({}) first."
                      .format(version))
            sys.stdout.flush()
            sys.stderr.flush()
            response = input("    Install quilt-specific pydoc-markdown? (y/n): ").lower()

        if response in ['n', 'no']:
            print("exiting..")
            exit()

        if version:
            pipmain(['uninstall', 'pydoc-markdown'])
        pipmain(['install', 'git+https://github.com/quiltdata/pydoc-markdown.git@google_docstrings'])

    import pydocmd

    if not pydocmd.__version__.endswith(EXPECTED_VERSION_SUFFIX):
        print("Please re-run this script to continue")
        exit()

    from pydocmd.__main__ import main as pydocmd_main

    # hacky, but we should maintain the same interpreter, and we're dependent on how
    # pydocmd calls mkdocs.
    if sys.argv[-1].endswith('build.py'):
        sys.argv.append('build')
    else:
        print("Using custom args for mkdocs.")

    pydocmd_main()
    print("Check the _build dir for generated files.")
