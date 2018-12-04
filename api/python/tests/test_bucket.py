import json
from mock import patch
from urllib.parse import urlparse

import botocore.session
from botocore.stub import Stubber

import pytest

from t4 import Bucket
from t4.data_transfer import s3_client
from t4.util import QuiltException

def test_bucket_construct():
    bucket = Bucket('s3://test-bucket')

def test_bucket_meta():
    with Stubber(s3_client) as stubber:
        test_meta = {
            'helium': json.dumps({'target': 'json'})
        }
        response = {
            'Metadata': test_meta,
            'ContentLength': 123
        }
        params = {
            'Bucket': 'test-bucket',
            'Key': 'test'
        }
        stubber.add_response('head_object', response, params)
        bucket = Bucket('s3://test-bucket')
        meta = bucket.get_meta('test')
        assert meta == {'target': 'json'}


        head_meta = {
            'helium': json.dumps({"target": "json"})
        }
        head_response = {
            'Metadata': head_meta,
            'ContentLength': 123
        }
        head_params = {
            'Bucket': 'test-bucket',
            'Key': 'test'
        }
        stubber.add_response('head_object', head_response, head_params)
        new_test_meta = {
            'helium': json.dumps({
                'target': 'json',
                'user_meta': {}
            })
        }
        response = {}
        params = {
            'CopySource': {
                'Bucket': 'test-bucket',
                'Key': 'test'
            },
            'Bucket': 'test-bucket',
            'Key': 'test',
            'Metadata': new_test_meta,
            'MetadataDirective': 'REPLACE'
        }
        stubber.add_response('copy_object', response, params)
        bucket.set_meta('test', {})

def test_bucket_fetch():
    with Stubber(s3_client) as stubber:
        response = {
            'IsTruncated': False
        }
        params = {
            'Bucket': 'test-bucket',
            'Prefix': 'does/not/exist/'
        }
        stubber.add_response('list_objects_v2', response, params)
        with pytest.raises(QuiltException):
            Bucket('s3://test-bucket').fetch('does/not/exist/', './')

def test_bucket_put():
    with patch("t4.bucket.copy_file") as copy_mock:
        bucket = Bucket('s3://test-bucket')
        bucket.put_file(key='README.md', path='./README') # put local file to bucket
        copy_src = copy_mock.call_args_list[0][0][0]
        assert urlparse(copy_src).scheme == 'file'
        copy_dest = copy_mock.call_args_list[0][0][1]
        assert urlparse(copy_dest).scheme == 's3'
