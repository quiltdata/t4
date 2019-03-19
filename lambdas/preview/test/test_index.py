"""
Test functions for preview endpoint
"""
import json
import pathlib

from unittest.mock import patch
import responses

from .. import index

MOCK_ORIGIN = 'http://localhost:3000'

BASE_DIR = pathlib.Path(__file__).parent / 'data'

# pylint: disable=no-member,invalid-sequence-index
class TestIndex():
    """Class to test various inputs to the main indexing function"""

    FILE_URL = f'{MOCK_ORIGIN}/file.ext'

    @classmethod
    def _make_event(cls, query, headers=None):
        return {
            'queryStringParameters': query or None,
            'headers': headers or None
        }

    def test_bad(self):
        """send a known bad event (no input query parameter)"""
        event = self._make_event({'url': self.FILE_URL}, {'origin': MOCK_ORIGIN})
        resp = index.lambda_handler(event, None)
        assert resp['statusCode'] == 400, "Expected 400 on event without 'input' query param"
        assert resp['body'], 'Expected explanation for 400'
        assert resp['headers']['access-control-allow-origin'] == '*'

    @responses.activate
    def test_ipynb(self):
        """test sending ipynb bytes"""
        notebook = BASE_DIR / 'nb_1200727.ipynb'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=notebook.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'ipynb'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        html_ = BASE_DIR / 'ipynb_html_response.txt'
        expected = html_.read_text().strip()
        assert resp['statusCode'] == 200, 'preview lambda failed on nb_1200727.ipynb'
        assert body['html'].strip() == expected, \
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
        event = self._make_event({'url': self.FILE_URL, 'input': 'parquet'})
        resp = index.lambda_handler(event, None)
        assert resp['statusCode'] == 200, f"Expected 200, got {resp['statusCode']}"
        body = json.loads(resp['body'])
        with open(info_response, 'r') as info_json:
            expected = json.load(info_json)
        assert (body['info'] == expected), \
            f"Unexpected body['info'] for {parquet}"

    @responses.activate
    def test_txt_long(self):
        """test sending txt bytes"""
        txt = BASE_DIR / 'long.txt'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=txt.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'txt'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        assert resp['statusCode'] == 200, 'preview lambda failed on long.txt'
        headlist = body['info']['data']['head']
        assert len(headlist) == index.MAX_LINES/2, 'unexpected number of lines in head'
        assert headlist[0] == 'Line 1', 'unexpected first line in head'
        assert headlist[-1] == f'Line {len(headlist)}', 'unexpected last line in head'
        taillist = body['info']['data']['tail']
        assert len(taillist) == index.MAX_LINES/2, 'expected empty tail'
        assert taillist[0] == f'Line 750', 'unexpected first line in head'
        assert taillist[-1] == f'Line 999', 'unexpected last line in head'

    @responses.activate
    @patch(__name__ + '.index.MAX_BYTES', 5)
    def test_txt_max(self):
        """test truncation to MAX_BYTES"""
        txt = BASE_DIR / 'one-line.txt'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=txt.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'txt'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        assert resp['statusCode'] == 200, 'preview lambda failed on long.txt'
        data = body['info']['data']
        assert body['info']['data']['head'][0] == '12345', 'failed to truncate to MAX_BYTES'
        assert len(data['tail']) == 0, 'expected empty tail'

    @responses.activate
    @patch(__name__ + '.index.MAX_BYTES', 5)
    def test_txt_max_two(self):
        """test truncation to MAX_BYTES"""
        txt = BASE_DIR / 'two-line.txt'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=txt.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'txt'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        assert resp['statusCode'] == 200, 'preview lambda failed on long.txt'
        data = body['info']['data']
        assert data['head'][0] == '1234', 'failed to truncate to MAX_BYTES'
        assert data['head'][1] == '5', 'failed to truncate to MAX_BYTES'
        assert len(data['tail']) == 0, 'expected empty tail'

    @responses.activate
    def test_txt_short(self):
        """test sending txt bytes"""
        txt = BASE_DIR / 'short.txt'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=txt.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'txt'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        assert resp['statusCode'] == 200, 'preview lambda failed on short.txt'
        headlist = body['info']['data']['head']
        assert len(headlist) == 98, 'unexpected number of lines head'
        assert headlist[0] == 'Line 1', 'unexpected first line in head'
        assert headlist[97] == 'Line 98', 'unexpected last line in head'
        taillist = body['info']['data']['tail']
        assert not taillist, 'expected empty tail'

    @responses.activate
    def test_vcf(self):
        """test sending vcf bytes"""
        vcf = BASE_DIR / 'example.vcf'
        responses.add(
            responses.GET,
            self.FILE_URL,
            body=vcf.read_bytes(),
            status=200)
        event = self._make_event({'url': self.FILE_URL, 'input': 'vcf'})
        resp = index.lambda_handler(event, None)
        body = json.loads(resp['body'])
        assert resp['statusCode'] == 200, 'preview lambda failed on example.vcf'
        data = body['info']['data']
        assert data['meta'][0] == '##fileformat=VCFv4.0', 'unexpected meta first line'
        assert data['meta'][5] == '##INFO=<ID=NS,Number=1,Type=Integer,Description="Number of Samples With Data">', 'unexpected meta fifth line'
        '##INFO=<ID=NS,Number=1,Type=Integer,Description="Number of Samples With Data">'
        assert data['header'][0] =='#CHROM POS     ID        REF ALT    QUAL FILTER INFO                              FORMAT      NA00001        NA00002        NA00003', 'unexpected header'
        assert data['data'][0] == '20     14370   rs6054257 G      A       29   PASS   NS=3;DP=14;AF=0.5;DB;H2           GT:GQ:DP:HQ 0|0:48:1:51,51 1|0:48:8:51,51 1/1:43:5:.,.', 'unexpected first data line'
        assert data['data'][-1] =='20     1234567 microsat1 GTCT   G,GTACT 50   PASS   NS=3;DP=9;AA=G                    GT:GQ:DP    0/1:35:4       0/2:17:2       1/1:40:3', 'unexpected last data line'

