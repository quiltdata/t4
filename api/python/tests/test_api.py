from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import time

import numpy as np
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

        content['default_local_registry'] = util.BASE_PATH.as_uri()
        content['default_remote_registry'] = None
        content['default_install_location'] = None
        content['registry_url'] = 'https://pkg.quiltdata.com'

        assert config == content

    @responses.activate
    def test_config_invalid_host(self):
        # Our URL handling is very forgiving, since we might receive a host
        # defined in local DNS, like 'foo' instead of 'foo.com' -- and on top
        # of that, we automatically add 'https://' to the name if no schema is
        # present.  ..but, a bad port causes an error..
        with pytest.raises(util.QuiltException, match='Port must be a number'):
            he.config('https://fliff:fluff')

    def test_put_to_directory_failure(self):
        # Adding pathes with trailing delimeters causes AWS to treat them like virtual directories
        # and can cause issues when downloading to host machine.
        test_object = "foo"
        with pytest.raises(ValueError):
            he.put(test_object, "s3://test/")

    def test_search_no_config(self):
        with pytest.raises(util.QuiltException, match="No configured region."):
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

    def test_put_copy_get(self):
        data = np.array([1, 2, 3])
        meta = {'foo': 'bar', 'x': 42}

        he.put(data, 'file.json', meta)
        he.copy('file.json', 'file2.json')
        data2, meta2 = he.get('file2.json')

        assert np.array_equal(data, data2)
        assert meta == meta2

    @patch('t4.session.get_session')
    @responses.activate
    def test_credentials_from_registry(self, get_session):
        mock_session = Mock()
        get_session.return_value = mock_session

        mock_response = Mock()
        mock_response.ok = True
        mock_session.post.return_value = mock_response

        mock_creds_response = Mock()
        exp = datetime.now(timezone.utc) + timedelta(hours=2)
        creds_data = {
            'AccessKeyId': 'asdf',
            'SecretAccessKey': 'asdf',
            'SessionToken': 'asdf',
            'Expiration': exp.isoformat()
        }
        mock_creds_response.json.return_value = creds_data
        mock_session.get.return_value = mock_creds_response

        he.session.set_credentials_from_registry()

        credentials = he.session.get_credentials()
        frozen_creds = credentials.get_frozen_credentials()
        assert frozen_creds.access_key == 'asdf'
        assert frozen_creds.secret_key == 'asdf'

    @responses.activate
    def test_empty_list_role(self):
        empty_list_response = { 'results': [] }
        responses.add(responses.GET, 'https://pkg.quiltdata.com/api/roles',
                json=empty_list_response, status=200)
        assert he.admin.list_roles() == []

    @responses.activate
    def test_list_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        list_response = { 'results': [result] }
        responses.add(responses.GET, 'https://pkg.quiltdata.com/api/roles',
                json=list_response, status=200)
        assert he.admin.list_roles() == [result]

    @responses.activate
    def test_get_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        responses.add(responses.GET, 'https://pkg.quiltdata.com/api/roles/1234-1234',
                json=result, status=200)
        assert he.admin.get_role('1234-1234') == result

    @responses.activate
    def test_create_role(self):
        result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        responses.add(responses.POST, 'https://pkg.quiltdata.com/api/roles',
                json=result, status=200)
        assert he.admin.create_role('test', 'asdf123') == result

    @responses.activate
    def test_edit_role(self):
        get_result = {
            'name': 'test',
            'arn': 'asdf123',
            'id': '1234-1234'
        }
        result = {
            'name': 'test_new_name',
            'arn': 'qwer456',
            'id': '1234-1234'
        }
        responses.add(responses.GET, 'https://pkg.quiltdata.com/api/roles/1234-1234',
                json=get_result, status=200)
        responses.add(responses.PUT, 'https://pkg.quiltdata.com/api/roles/1234-1234',
                json=result, status=200)
        assert he.admin.edit_role('1234-1234', 'test_new_name', 'qwer456') == result

    @responses.activate
    def test_delete_role(self):
        responses.add(responses.DELETE, 'https://pkg.quiltdata.com/api/roles/1234-1234',
                status=200)
        he.admin.delete_role('1234-1234')

    @responses.activate
    def test_set_role(self):
        responses.add(responses.POST, 'https://pkg.quiltdata.com/api/users/set_role',
                json={}, status=200)

        not_found_result = {
            'message': "No user exists by the provided name."
        }
        responses.add(responses.POST, 'https://pkg.quiltdata.com/api/users/set_role',
                json=not_found_result, status=400)

        he.admin.set_role('test_user', 'test_role')

        with pytest.raises(util.QuiltException):
            he.admin.set_role('not_found', 'test_role')
