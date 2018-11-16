import json

import botocore.session
from botocore.stub import Stubber

from t4 import Bucket
from t4.data_transfer import s3_client

def test_bucket_construct():
    bucket = Bucket('s3://test-bucket')

def test_bucket_meta():
    with Stubber(s3_client) as stubber:
        test_meta = {
            'helium': json.dumps({'target': 'json'})
        }
        response = {
            'Metadata': test_meta
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
            'Metadata': head_meta
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

