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
    """Class to test various inputs to the main indexing function"""

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
            event = self.S3_EVENT.copy()
            event['queryStringParameters'].update({'input': 'ipynb'})
            resp = lambda_handler(event, None)
            body = json.loads(resp['body'])
            html_ = os.path.join(basedir, 'ipynb_html_response.txt')
            body_html = open(html_, 'r').read()
            assert body['html'].startswith(body_html), \
                f"Unexpected HTML:\n{body['html']}"

    @patch.dict(os.environ, {'WEB_ORIGIN': MOCK_ORIGIN})
    @responses.activate
    def test_parquet(self):
        """test sending parquet bytes"""
        parent = os.path.dirname(__file__)
        basedir = os.path.join(parent, 'data')
        parquet = os.path.join(basedir, 'atlantic_storms.parquet')
        info_response = os.path.join(basedir, 'parquet_info_response.json')
        with open(parquet, 'rb') as file_:
            responses.add(
                responses.GET,
                self.FILE_URL,
                body=file_.read(),
                status=200)
            event = self.S3_EVENT.copy()
            event['queryStringParameters'].update({'input': 'parquet'})
            resp = lambda_handler(event, None)
            assert resp['statusCode'] == 200, f"Expected 200, got {resp['statusCode']}"
            body = json.loads(resp['body'])
            with open(info_response, 'r') as info_json:
                expected = json.loads(info_json.read())
                assert (body['info'] == expected), \
                    f"Unexpected body['info'] for {parquet}"
