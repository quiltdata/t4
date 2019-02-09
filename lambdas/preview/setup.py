from setuptools import setup

setup(
    name='lambda_function',
    version='0.0.1',
    py_modules=['index'],
    install_requires=[
        'jsonschema==2.6.0',
        'nbconvert==5.3.1',
        'pandas==0.24.1',
        'pyarrow==0.12',
        'requests==2.20.0',
    ],
    extras_require={
        'tests': [
            'codecov',
            'pytest',
            'responses',
            'pytest-cov',
        ],
    },
)
