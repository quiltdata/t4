import json
from mock import patch
from unittest.mock import MagicMock

from t4 import Bucket

class ResponseMock(object):
    pass


def get_configured_bucket():
    with patch('t4.bucket.requests') as requests_mock:
        mock_config = {
                'configs': {
                    'quilt-example': {
                        'search_endpoint': 'test'
                    }
                }
            }
        mock_response = ResponseMock()
        setattr(mock_response, 'text', json.dumps(mock_config))
        setattr(mock_response, 'ok', True)
        def mock_get(url):
            return mock_response
        requests_mock.get = mock_get
        b = Bucket('s3://quilt-example')
        return b

def test_bucket_config():
    b = get_configured_bucket()
    assert b._search_endpoint == 'test'

def test_bucket_search():
    with patch('t4.search_util._create_es') as create_es_mock:
        es_mock = MagicMock()
        create_es_mock.return_value = es_mock
        b = Bucket('s3://quilt-example')
        b.search('*')
        assert es_mock.search.called_with('*', 'test')
