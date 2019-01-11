from setuptools import setup

setup(
    name='lambda_function',
    version='0.0.1',
    py_modules=['index'],
    install_requires=[
        'nbconvert==5.3.1',
        'pandas==0.23.4',
        'pyarrow==0.11.1',
        's3fs==0.2.0',
        'urllib3==1.24.1',
    ],
)
