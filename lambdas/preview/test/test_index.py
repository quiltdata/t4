"""
Test functions for preview endpoint
"""
import json
import os

from unittest.mock import patch
import responses

from ..index import lambda_handler

MOCK_ORIGIN = 'https://mock.quiltdata.com'

# pylint: disable=no-member
class TestIndex():
    """Class kto test various inputs to the main indexing function"""

    FILE_URL = f'{MOCK_ORIGIN}/file.ext'

    S3_EVENT = {
        'headers': {
            'origin': MOCK_ORIGIN
        },
        'queryStringParameters': {
            'url': FILE_URL
        }
    }

    def test_bad(self):
        """send a known bad event (no input query parameter)"""
        resp = lambda_handler(self.S3_EVENT, None)
        assert resp['statusCode'] == 400, "Expected 400 on event without 'input' query param"
        assert resp['body'], 'Expected explanation for 400'

    @patch.dict(os.environ, {'WEB_ORIGIN': MOCK_ORIGIN})
    @responses.activate
    def test_ipynb(self):
        """test sending ipynb bytes"""
        parent = os.path.dirname(__file__)
        basedir = os.path.join(parent, 'data')
        notebook = os.path.join(basedir, 'nb_1200727.ipynb')
        with open(notebook, 'rb') as file_:
            responses.add(
                responses.GET,
                self.FILE_URL,
                body=file_.read(),
                status=200)
            # make it an ipynb event
            self.S3_EVENT['queryStringParameters']['input'] = 'ipynb'
            resp = lambda_handler(self.S3_EVENT, None)
            body = json.loads(resp['body'])
            assert body['info'] == '{}', 'Expected empty info object'
            html_ = os.path.join(basedir, 'html.txt')
            BODY_HTML = open(html_, 'r').read()
            assert body['html'].startswith(BODY_HTML), \
                f"Unexpected HTML:\n{body['html']}"

    @patch.dict(os.environ, {'WEB_ORIGIN': MOCK_ORIGIN})
    @responses.activate
    def test_parquet(self):
        """test sending parquet bytes"""
        parent = os.path.dirname(__file__)
        basedir = os.path.join(parent, 'data')
        parquet = os.path.join(basedir, 'atlantic_storms.parquet')
        with open(parquet, 'rb') as file_:
            responses.add(
                responses.GET,
                self.FILE_URL,
                body=file_.read(),
                status=200)
            # make it an ipynb event
            self.S3_EVENT['queryStringParameters']['input'] = 'parquet'
            resp = lambda_handler(self.S3_EVENT, None)
            assert resp['statusCode'] == 200, f"Expected 200, got {resp['statusCode']}"
            body = json.loads(resp['body'])
            for k in ['html', 'info']:
                assert  body[k], "Expected key '{k}' to be defined"
