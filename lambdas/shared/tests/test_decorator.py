"""
Decorator tests
"""

from unittest import TestCase

from t4_lambda_shared.decorator import api, validate

# pylint: disable=invalid-sequence-index
class TestDecorator(TestCase):
    def test_api_basic(self):
        @api(cors_origins=['https://example.com'])
        def handler(query, headers):
            assert query == {}
            assert headers == {}
            return 200, 'foo', {'Content-Type': 'text/plain'}

        resp = handler({
            'queryStringParameters': None,
            'headers': None
        }, None)

        assert resp['statusCode'] == 200
        assert resp['body'] == 'foo'
        assert resp['headers'] == {'Content-Type': 'text/plain'}

    def test_api_query_headers(self):
        @api(cors_origins=['https://example.com'])
        def handler(query, headers):
            assert headers == {'content-length': '123'}
            assert query == {'foo': 'bar'}
            return 200, 'foo', {'Content-Type': 'text/plain'}

        resp = handler({
            'queryStringParameters': {
                'foo': 'bar'
            },
            'headers': {
                'content-length': '123'
            }
        }, None)

        assert resp['statusCode'] == 200
        assert resp['body'] == 'foo'
        assert resp['headers'] == {'Content-Type': 'text/plain'}

    def test_api_cors(self):
        @api(cors_origins=['https://example.com'])
        def handler(query, headers):
            return 200, 'foo', {'Content-Type': 'text/plain'}

        # Request with a correct origin.
        resp = handler({
            'queryStringParameters': {
                'foo': 'bar'
            },
            'headers': {
                'origin': 'https://example.com'
            }
        }, None)

        assert resp['statusCode'] == 200
        assert resp['body'] == 'foo'
        assert resp['headers'] == {
            'Content-Type': 'text/plain',
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'HEAD,GET,POST',
            'access-control-allow-headers': '*',
            'access-control-max-age': 86400
        }

        # Request with a bad origin.
        resp = handler({
            'queryStringParameters': {
                'foo': 'bar'
            },
            'headers': {
                'origin': 'https://quiltdata.com'
            }
        }, None)

        assert resp['statusCode'] == 200
        assert resp['body'] == 'foo'
        assert resp['headers'] == {
            'Content-Type': 'text/plain',
        }

        # Request with no origin.
        resp = handler({
            'queryStringParameters': {
                'foo': 'bar'
            },
            'headers': None
        }, None)

        assert resp['statusCode'] == 200
        assert resp['body'] == 'foo'
        assert resp['headers'] == {
            'Content-Type': 'text/plain',
        }

    def test_api_exception(self):
        @api(cors_origins=['https://example.com'])
        def handler(query, header):
            raise TypeError("Fail!")

        resp = handler({
            'queryStringParameters': {
                'foo': 'bar'
            },
            'headers': {
                'origin': 'https://example.com'
            }
        }, None)

        assert resp['statusCode'] == 500
        assert resp['body'] == 'Internal Server Error'
        assert resp['headers'] == {
            'Content-Type': 'text/plain',
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'HEAD,GET,POST',
            'access-control-allow-headers': '*',
            'access-control-max-age': 86400
        }

    def test_validator(self):
        schema = {
            'type': 'object',
            'properties': {
                'foo': {
                    'type': 'string'
                },
            },
            'required': ['foo'],
            'additionalProperties': False
        }

        @validate(schema)
        def handler(query, headers):
            assert query == {'foo': 'bar'}
            assert headers == {}
            return 200, 'blah', {}

        code, body, headers = handler({'foo': 'bar'}, {})
        assert code == 200
        assert body == 'blah'
        assert headers == {}

        code, _, headers = handler({}, {})
        assert code == 400
        assert headers == {'Content-Type': 'text/plain'}

        code, _, headers = handler({'foo': 'bar', 'x': 'y'}, {})
        assert code == 400
        assert headers == {'Content-Type': 'text/plain'}
