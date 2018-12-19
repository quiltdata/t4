from setuptools import setup

setup(
    name='es_indexer',
    version='0.0.1',
    py_modules=['lam'],
    install_requires=[
        'aws-requests-auth==0.4.2',
        'elasticsearch==6.3.1',
        'nbconvert>=5.4',
    ],
)
