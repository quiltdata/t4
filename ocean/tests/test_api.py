
import pytest
import requests
import responses
from ruamel.yaml import YAML

import helium as he
from helium import util



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
