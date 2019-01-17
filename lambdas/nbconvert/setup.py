from setuptools import setup

setup(
    name='lambda_function',
    version='0.0.1',
    py_modules=['index'],
    install_requires=[
        'jsonschema==2.6.0',
        'nbconvert==5.3.1',
        'pandas==0.23.4',
        'pyarrow==0.11.1',
        'requests==2.20.0',
    ],
)
