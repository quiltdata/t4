from setuptools import setup, find_packages

def readme():
    readme_short = """
    """
    return readme_short

setup(
    name="helium",
    version="0.0.1-dev",
    packages=find_packages(),
    description='Helium',
    long_description=readme(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    author='quiltdata',
    author_email='contact@quiltdata.io',
    license='LICENSE',
    url='https://github.com/quiltdata/quilt-new',
    keywords='',
    install_requires=[
        'appdirs>=1.4.0',
        'aws-requests-auth>=0.4.2',
        'boto3',
        'elasticsearch~=6.3.1',
        'enum34; python_version<"3.0"',     # stdlib backport
        'future>=0.16.0',                   # stdlib backport: 'from builtins import xxx', plus others.
        'numpy>=1.14.0',                    # required by pandas, but missing from its dependencies.
        'packaging>=16.8',
        'pandas>=0.19.2',
        'pathlib2; python_version<="3.5"',  # stdlib backport
        'pyarrow>=0.9.0',
        'requests>=2.12.4',
        'ruamel.yaml<=0.15.70',
        'six>=1.10.0',
        'tqdm>=4.26.0',
    ],
    extras_require={
        'tests': [
            'mock; python_version<"3.5"',   # XXX correct syntax for extras_require?
            'pytest',
            'pytest-cov',
            'responses',
            'tox',
            'detox',
            'tox-pytest-summary',
        ],
    },
    include_package_data=True,
    entry_points={
        # 'console_scripts': ['quilt=quilt.tools.main:main'],
    }
)
