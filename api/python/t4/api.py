import glob
from itertools import chain
import json
import os
import requests

from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection
from six.moves import urllib
from urllib.parse import urlparse, urlunparse

from .data_transfer import (TargetType, copy_file, deserialize_obj, download_bytes,
                            upload_bytes, delete_object, list_objects,
                            list_object_versions, serialize_obj)
from .packages import get_local_package_registry, get_package_registry
from .util import (HeliumConfig, QuiltException, AWS_SEPARATOR, CONFIG_PATH,
                   CONFIG_TEMPLATE, fix_url, parse_file_url, parse_s3_url, read_yaml, validate_url,
                   write_yaml, yaml_has_comments)

# backports
from six.moves import urllib
try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib


def copy(src, dest):
    """
    Copies ``src`` object from T4 to ``dest``

    Either of ``src`` and ``dest`` may be S3 paths (starting with ``s3://``)
    or local file paths (starting with ``file:///``).

    Parameters:
        src (str): a path to retrieve
        dest (str): a path to write to
    """
    copy_file(fix_url(src), fix_url(dest))


def put(obj, dest, meta=None):
    """Write an in-memory object to the specified T4 ``dest``

    Note:
        Does not work with all objects -- object must be serializable.

    You may pass a dict to ``meta`` to store it with ``obj`` at ``dest``.

    See User Docs for more info on object Serialization and Metadata.

    Parameters:
        obj: a serializable object
        dest (str): path in T4
        meta (dict): Optional. metadata dict to store with ``obj`` at ``dest``
    """
    if dest.endswith(AWS_SEPARATOR):
        raise ValueError("Invalid path: %r; ends with a %r"
                         % (dest, AWS_SEPARATOR))
    data, target = serialize_obj(obj)
    all_meta = dict(
        target=target.value,
        user_meta=meta
    )

    upload_bytes(data, dest, all_meta)


def get(src, version=None):
    """Retrieves src object from T4 and loads it into memory.

    An optional ``version`` may be specified.

    Parameters:
        src (str): A path specifying the object to retrieve
        version (str): Optional. A specific S3 version id to use

    Returns:
        tuple: ``(data, metadata)``.  Does not work on all objects.
    """
    data, meta = download_bytes(src, version)

    target_str = meta.get('target')
    if target_str is None:
        raise QuiltException("No serialization metadata")

    try:
        target = TargetType(target_str)
    except ValueError:
        raise QuiltException("Unknown serialization target: %r" % target_str)
    return deserialize_obj(data, target), meta.get('user_meta')


def delete(path):
    """Delete an object from T4.

    Does not delete local files.

    Parameters:
        path (str): Path of object to delete
    """
    delete_object(path)


def ls(path, recursive=False):
    """List data from the specified path.

    Parameters:
        path (str): Path (including bucket name) to list
        recursive (bool): show subdirectories and their contents as well

    Returns:
        ``list``: Return value structure has not yet been permanently decided
        Currently, it's a ``tuple`` of ``list`` objects, containing the
        following:
        result[0]
            directory info
        result[1]
            file/object info
        result[2]
            delete markers
    """
    if not path.endswith('/'):
        path += '/'

    results = list_object_versions(path, recursive=recursive)

    return results


def list_packages(registry=None):
    """ Lists Packages in the registry.

    Returns a list of all named packages in a registry.
    If the registry is None, default to the local registry.

    Args:
        registry(string): location of registry to load package from.

    Returns:
        A list of strings containing the names of the packages        
    """
    if not registry:
        registry = 'whatever'
    registry = get_package_registry(fix_url(registry)).strip("/") + '/named_packages'

    registry_url = urlparse(registry)
    if registry_url.scheme == 'file':
        registry_dir = pathlib.Path(parse_file_url(registry_url))
        return [str(x.relative_to(registry_dir)) for x in registry_dir.glob('*/*')]

    elif registry_url.scheme == 's3':
        src_bucket, src_path, _ = parse_s3_url(registry_url)
        prefixes, _ = list_objects(src_bucket + '/' + src_path + '/', recursive=False)
        # Pull out the directory fields and remove the src_path prefix.
        names = []
        # Search each org directory for named packages.
        for org in [x['Prefix'][len(src_path):].strip('/') for x in prefixes]:
            packages, _ = list_objects(src_bucket + '/' + src_path + '/' + org, recursive=False)
            names.append([y['Prefix'][len(src_path):].strip('/') for y in packages])
        return names

    else:
        raise NotImplementedError



########################################
# Search
########################################

es_index = 'drive'

def _create_es():
    config_obj = config()
    es_url = config_obj.get('elastic_search_url', None)
    if es_url is None:
        raise QuiltException('No configured elastic_search_url. '
                              'Please use he.config')
    es_url = urllib.parse.urlparse(es_url)

    aws_region = config_obj.get('region')
    if aws_region is None:
        raise QuiltException('No configured region. '
                              'Please use he.config')

    auth = BotoAWSRequestsAuth(aws_host=es_url.hostname,
                               aws_region=aws_region,
                               aws_service='es')
    port = es_url.port or (443 if es_url.scheme == 'https' else 80)

    es = Elasticsearch(
        hosts=[{'host': es_url.hostname, 'port': port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    return es

def search(query):
    """
    Searches your bucket. query can contain plaintext, and can also contain clauses
    like $key:"$value" that search for exact matches on specific keys.

    Returns either the request object (in case of an error) or a list of objects with the following keys:
        key: key of the object
        version_id: version_id of object version
        operation: Create or Delete
        meta: metadata attached to object
        size: size of object in bytes
        text: indexed text of object
        source: source document for object (what is actually stored in ElasticSeach)
        time: timestamp for operation
    """
    es = _create_es()

    payload = {'query': {'query_string': {
        'default_field': 'content',
        'query': query,
        'quote_analyzer': 'keyword',
        }}}

    r = es.search(index=es_index, body=payload)

    try:
        results = []
        for result in r['hits']['hits']:
            key = result['_source']['key']
            vid = result['_source']['version_id']
            op = result['_source']['type']
            meta = json.dumps(result['_source']['user_meta'])
            size = str(result['_source']['size'])
            text = result['_source']['text']

            time = str(result['_source']['updated'])
            results.append({
                'key': key,
                'version_id': vid,
                'operation': op,
                'meta': meta,
                'size': size,
                'text': text,
                'source': result['_source'],
                'time': time
            })
        results = list(sorted(results, key=lambda x: x['time'], reverse=True))
        return results
    except KeyError as e:
        return r

def _print_table(table, padding=2):
    cols_width = [max(len(word) for word in col) for col in zip(*table)]
    for row in table:
        print((" " * padding).join(word.ljust(width) for word, width in zip(row, cols_width)))

def log(key, pprint=False):
    es = _create_es()

    payload = {'query': {'constant_score': {'filter': {'term': {
        'key': key
    }}}}}

    r = es.search(index=es_index, body=payload)

    try:
        table = []
        for result in r['hits']['hits']:
            if result['_source']['key'] != key:
                continue
            vid = result['_source']['version_id']
            op = result['_source']['type']
            meta = json.dumps(result['_source']['user_meta'])
            size = str(result['_source']['size'])
            text = result['_source'].get('text', '')

            time = str(result['_source']['updated'])
            table.append({
                'version_id': vid,
                'operation': op,
                'meta': meta,
                'size': size,
                'text': text,
                'time': time
            })
        table = list(sorted(table, key=lambda x: x['time'], reverse=True))
        if pprint:
            ptable = [('Date', 'Version ID', 'Operation', 'Size', 'Meta')]
            for t in table:
                ptable.append((t['time'], t['version_id'], t['operation'],
                               t['size'], t['meta']))
            _print_table(ptable)
        return table
    except KeyError as e:
        return r

def config(*autoconfig_url, **config_values):
    """Set or read the T4 configuration

    To retrieve the current config, call directly, without arguments:
        >>> import t4 as he
        >>> he.config()

    To trigger autoconfiguration, call with just the navigator URL:
        >>> he.config('https://example.com')

    To set config values, call with one or more key=value pairs:
        >>> he.config(navigator_url='http://example.com',
        ...           elastic_search_url='http://example.com/queries')
    When setting config values, unrecognized values are rejected.  Acceptable
    config values can be found in `t4.util.CONFIG_TEMPLATE`

    :param autoconfig_url: URL indicating a location to configure from
    :param **config_values: `key=value` pairs to set in the config
    :returns: HeliumConfig object (an ordered Mapping)
    """
    if autoconfig_url and config_values:
        raise QuiltException("Expected either an auto-config URL or key=value pairs, but got both.")
    # Total distinction of args and kwargs -- config(autoconfig_url='http://foo.com')
    if autoconfig_url and len(autoconfig_url) > 1:
        raise QuiltException("Expected a single autoconfig URL argument, not multiple args.")

    config_template = read_yaml(CONFIG_TEMPLATE)
    if autoconfig_url:
        autoconfig_url = autoconfig_url[0]
        config_url = autoconfig_url.rstrip('/') + '/config.json'

        if config_url[:7] not in ('http://', 'https:/'):
            config_url = 'https://' + config_url

        validate_url(config_url)

        # TODO: handle http basic auth via URL if using https (https://user:pass@hostname/path)
        response = requests.get(config_url)
        if not response.ok:
            message = "An HTTP Error ({code}) occurred: {reason}"
            raise QuiltException(
                message.format(code=response.status_code, reason=response.reason),
                response=response
                )
        new_config = read_yaml(response.text)  # handles JSON and YAML (YAML is a superset of JSON)

        for key, value in new_config.items():
            # No key validation, per current fast dev rate on config.json.
            # if key not in config_template:
            #     raise QuiltException("Unrecognized configuration key from {}: {}".format(config_url, key))
            if value and key.endswith('_url'):
                validate_url(value)
        # Use their config + our defaults, keeping their comments
        if yaml_has_comments(new_config):
            # add defaults for keys missing from their config
            for key in set(config_template) - set(new_config):
                new_config[key] = config_template[key]
            write_yaml(new_config, CONFIG_PATH, keep_backup=True)
            return HeliumConfig(CONFIG_PATH, new_config)
        # Use our config + their configured values, keeping our comments.
        else:
            for key, value in new_config.items():
                config_template[key] = value
            write_yaml(config_template, CONFIG_PATH, keep_backup=True)
            return HeliumConfig(CONFIG_PATH, config_template)
    # No autoconfig URL given -- use local config
    if CONFIG_PATH.exists():
        local_config = read_yaml(CONFIG_PATH)
    else:
        local_config = config_template

    if config_values:
        for key, value in config_values.items():
            # No key validation, per current fast dev rate on config.json.
            # if key not in config_template:
            #     raise QuiltException("Unrecognized configuration key: {}".format(key))
            if value and key.endswith('_url'):
                validate_url(value)
            local_config[key] = value
        write_yaml(local_config, CONFIG_PATH, keep_backup=True)

    return HeliumConfig(CONFIG_PATH, local_config)
