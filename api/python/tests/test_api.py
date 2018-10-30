from unittest.mock import Mock, patch

import pytest
import responses
from ruamel.yaml import YAML

import t4 as he
from t4 import util

class TestAPI():
    @responses.activate
    def test_config(self):
        content = {
            'navigator_url': 'https://foo.bar',
            'elastic_search_url': 'https://es.foo',
            'accept_invalid_config_keys': 'yup',
            }
        responses.add(responses.GET, 'https://foo.bar/config.json', json=content, status=200)

        he.config('foo.bar')

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://foo.bar/config.json'

        yaml = YAML()
        config = yaml.load(util.CONFIG_PATH)

        assert config == content

    @responses.activate
    def test_config_invalid_host(self):
        # Our URL handling is very forgiving, since we might receive a host
        # defined in local DNS, like 'foo' instead of 'foo.com' -- and on top
        # of that, we automatically add 'https://' to the name if no schema is
        # present.  ..but, a bad port causes an error..
        with pytest.raises(util.HeliumException, match='Port must be a number'):
            he.config('https://fliff:fluff')

    def test_put_to_directory_failure(self):
        # Adding pathes with trailing delimeters causes AWS to treat them like virtual directories
        # and can cause issues when downloading to host machine.
        test_object = "foo"
        with pytest.raises(ValueError):
            he.put(test_object, "test/")

    def test_search_no_config(self):
        with pytest.raises(util.HeliumException, match="No configured region."):
            he.search('*')

    @patch('t4.api._create_es')
    def test_search(self, _create_es):
        mock_es_client = Mock()
        mock_es_client.search.return_value = {
            'took': 3,
            'timed_out': False,
            '_shards': {'total': 5, 'successful': 5, 'skipped': 0, 'failed': 0},
            'hits': {'total': 0, 'max_score': None, 'hits': []}
        }

        _create_es.return_value = mock_es_client
        query = '*'
        payload = {'query': {'query_string': {
            'default_field': 'content',
            'query': query,
            'quote_analyzer': 'keyword',
        }}}

        result = he.search(query)
        assert mock_es_client.search.called
        mock_es_client.search.assert_called_with(index=he.api.es_index, body=payload)

        assert isinstance(result, list)
        assert result == []

