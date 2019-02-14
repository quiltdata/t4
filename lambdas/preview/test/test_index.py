"""
Test functions for preview endpoint
"""
import json
import os
import pathlib

import responses

from ..index import lambda_handler

MOCK_ORIGIN = 'http://localhost:3000'

BASE_DIR = pathlib.Path(__file__).parent / 'data'

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

    @responses.activate
    def test_ipynb(self):
        """test sending ipynb bytes"""
        notebook = BASE_DIR / 'nb_1200727.ipynb'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=notebook.read_bytes(),
            status=200)
        event = self.S3_EVENT.copy()
        event['queryStringParameters'].update({'input': 'ipynb'})
        resp = lambda_handler(event, None)
        body = json.loads(resp['body'])
        html_ = BASE_DIR / 'ipynb_html_response.txt'
        body_html = html_.read_text()
        assert body['html'].startswith(body_html), \
            f"Unexpected HTML:\n{body['html']}"

    @responses.activate
    def test_parquet(self):
        """test sending parquet bytes"""
        parquet = BASE_DIR / 'atlantic_storms.parquet'
        info_response = BASE_DIR / 'parquet_info_response.json'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=parquet.read_bytes(),
            status=200)
        event = self.S3_EVENT.copy()
        event['queryStringParameters'].update({'input': 'parquet'})
        resp = lambda_handler(event, None)
        assert resp['statusCode'] == 200, f"Expected 200, got {resp['statusCode']}"
        body = json.loads(resp['body'])
        with open(info_response, 'r') as info_json:
            expected = json.load(info_json)
        assert (body['info'] == expected), \
            f"Unexpected body['info'] for {parquet}"
