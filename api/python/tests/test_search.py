import json
from mock import patch
from unittest.mock import MagicMock

from t4 import Bucket

class ResponseMock(object):
    pass


def get_configured_bucket():
    with patch('t4.bucket.requests') as requests_mock:
        mock_config = {
                'buckets': [
                    {
                        'name': 'test-bucket',
                        'searchEndpoint': 'test'
                    }
                ]
            }
        mock_response = ResponseMock()
        setattr(mock_response, 'text', json.dumps(mock_config))
        setattr(mock_response, 'ok', True)
        def mock_get(url):
            return mock_response
        requests_mock.get = mock_get
        bucket = Bucket('s3://test-bucket')
        bucket.config()
        return bucket

def test_bucket_config():
    bucket = get_configured_bucket()
    assert bucket._search_endpoint == 'test'

def test_bucket_search():
    with patch('t4.search_util._create_es') as create_es_mock:
        es_mock = MagicMock()
        es_mock.search.return_value = {
            'hits': {
                'hits': [{
                    '_source': {
                        'key': 'asdf',
                        'version_id': 'asdf',
                        'type': 'asdf',
                        'user_meta': {},
                        'size': 0,
                        'text': '',
                        'updated': '0'
                    }
                }]
            }
        }
        create_es_mock.return_value = es_mock
        bucket = get_configured_bucket()
        results = bucket.search('*')
        assert es_mock.search.called_with('*', 'test')
        assert len(results) == 1
