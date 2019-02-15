from setuptools import setup

setup(
    name='t4_lambda_preview',
    version='0.0.1',
    py_modules=['index'],
    extras_require={
        'tests': [
            'codecov',
            'pytest',
            'responses',
            'pytest-cov',
        ],
    },
)
