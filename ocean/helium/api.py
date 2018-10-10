import json
import os
import subprocess
import pandas as pd
import re
import requests
import sys

from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection
from six.moves import urllib
from six import BytesIO, binary_type, text_type
from enum import Enum

from .data_transfer import (download_bytes, download_file, upload_bytes, upload_file,
                            delete_object, list_objects, list_object_versions)
from .snapshots import (create_snapshot, download_bytes_from_snapshot,
                        download_file_from_snapshot, read_snapshot_by_hash,
                        get_snapshots)
from .util import (HeliumException, AWS_SEPARATOR, CONFIG_PATH, CONFIG_TEMPLATE, read_yaml,
                   split_path, validate_url, write_yaml, yaml_has_comments)


class TargetType(Enum):
    """
    Enums for target types
    """
    BYTES = 'bytes'
    UNICODE = 'unicode'
    JSON = 'json'
    PYARROW = 'pyarrow'
    NUMPY = 'numpy'


def put_file(src, dest, meta=None):
    all_meta = dict(
        user_meta=meta
    )
    upload_file(src, dest, all_meta)


def get_file(src, dest, snapshot=None, version=None):
    if version is not None and snapshot is not None:
        raise HeliumException("Specify only one of snapshot or version.")
    
    if snapshot is not None:
        download_file_from_snapshot(src, dest, snapshot)
    else:
        download_file(src, dest, version=version)


def _get_target_for_object(obj):
    # TODO: Lazy loading.
    import numpy as np
    import pandas as pd

    if isinstance(obj, binary_type):
        target = TargetType.BYTES
    elif isinstance(obj, text_type):
        target = TargetType.UNICODE
    elif isinstance(obj, dict):
        target = TargetType.JSON
    elif isinstance(obj, np.ndarray):
        target = TargetType.NUMPY
    elif isinstance(obj, pd.DataFrame):
        target = TargetType.PYARROW
    else:
        raise HeliumException("Unsupported object type")
    return target


def _serialize_obj(obj):
    target = _get_target_for_object(obj)

    if target == TargetType.BYTES:
        data = obj
    elif target == TargetType.UNICODE:
        data = obj.encode('utf-8')
    elif target == TargetType.JSON:
        data = json.dumps(obj).encode('utf-8')
    elif target == TargetType.NUMPY:
        import numpy as np
        buf = BytesIO()
        np.save(buf, obj, allow_pickle=False)
        data = buf.getvalue()
    elif target == TargetType.PYARROW:
        import pyarrow as pa
        from pyarrow import parquet
        buf = BytesIO()
        table = pa.Table.from_pandas(obj)
        parquet.write_table(table, buf)
        data = buf.getvalue()
    else:
        raise HeliumException("Don't know how to serialize object")

    return data, target


def _deserialize_obj(data, target):
    if target == TargetType.BYTES:
        obj = data
    elif target == TargetType.UNICODE:
        obj = data.decode('utf-8')
    elif target == TargetType.JSON:
        obj = json.loads(data.decode('utf-8'))
    elif target == TargetType.NUMPY:
        import numpy as np
        buf = BytesIO(data)
        obj = np.load(buf, allow_pickle=False)
    elif target == TargetType.PYARROW:
        import pyarrow as pa
        from pyarrow import parquet
        buf = BytesIO(data)
        table = parquet.read_table(buf)
        obj = pa.Table.to_pandas(table)
    else:
        raise NotImplementedError

    return obj


def put(obj, dest, meta=None):
    if dest.endswith(AWS_SEPARATOR):
        raise ValueError("Invalid path: %r; ends with a %r"
                         % (dest, AWS_SEPARATOR))
    data, target = _serialize_obj(obj)
    all_meta = dict(
        target=target.value,
        user_meta=meta
    )

    upload_bytes(data, dest, all_meta)


def get(src, snapshot=None, version=None):
    if snapshot is not None and version is not None:
        raise HeliumException("Specify only one of snapshot or version.")
    if snapshot is not None:
        data, meta = download_bytes_from_snapshot(src, snapshot)
    else:
        data, meta = download_bytes(src, version)
    
    target_str = meta.get('target')
    if target_str is None:
        raise HeliumException("No serialization metadata")

    try:
        target = TargetType(target_str)
    except ValueError:
        raise HeliumException("Unknown serialization target: %r" % target_str)
    return _deserialize_obj(data, target), meta.get('user_meta')


def delete(path):
    delete_object(path)


def ls(path, recursive=False):
    if not path.endswith('/'):
        path += '/'

    results = list_object_versions(path, recursive=recursive)

    return results


########################################
# Snapshots
########################################

class DisplayList(list):
    """
    Wrapper around the list of dicts returned by status, diff and compare
    to show the results clearly in iPython and Jupyter.
    """

    def __init__(self, src, columns=None, index=None):
        self._displayargs = {}
        if columns:
            self._displayargs['columns'] = columns

        if index:
            self._displayargs['index'] = index
        super(DisplayList, self).__init__(src)

    def _repr_html_(self):
        df = pd.DataFrame.from_records(self, **self._displayargs)
        return df.to_html()


def snapshot(path, message):
    return create_snapshot(path, message)


def list_snapshots(bucket, contains=None):
    snapshots_list = get_snapshots(bucket, contains)
    return DisplayList(snapshots_list, columns=['hash', 'path', 'timestamp', 'message'], index='path')


def diff(bucket, src, dst):
    src_path = dst_path = None
    if src != 'latest':
        src_snapshot = read_snapshot_by_hash(bucket, src)
        src_path = src_snapshot.get('path', None)

    if dst != 'latest':
        dst_snapshot = read_snapshot_by_hash(bucket, dst)
        dst_path = dst_snapshot.get('path', None)

    # TODO: Raise exception instead
    assert src_path or dst_path

    if src_path:
        src_objects = src_snapshot['contents']
    else:
        src_list = list_objects(f"{bucket}/{dst_path}")
        src_objects = {obj['Key']: {'ETag': obj['ETag'], 'VersionId': None} for obj in src_list}
        
    if dst_path:
        dst_objects = dst_snapshot['contents']
    else:
        dst_list = list_objects(f"{bucket}/{src_path}")
        dst_objects = {obj['Key']: {'ETag': obj['ETag'], 'VersionId': None} for obj in dst_list}

    # Iterate through current objects
    diff = []
    for key, src_obj in src_objects.items():
        etag = src_obj['ETag']
        if key in dst_objects:
            if etag != dst_objects[key]['ETag']:
                diff.append(dict(Key=key, ETag=etag, status="Modified"))
            del dst_objects[key]
        else:
            diff.append(dict(Key=key, ETag=etag, status="Deleted"))

    for key, attrs in dst_objects.items():
        diff.append(dict(Key=key, ETag=attrs['ETag'], status="Added"))

    return DisplayList(diff, columns=['status', 'Key', 'ETag'], index='status')


########################################
# Search
########################################

es_index = 'drive'

def _create_es():
    config_obj = config()
    es_url = config_obj.get('elastic_search_url', None)
    if es_url is None:
        raise HeliumException('No configured elastic_search_url. '
                              'Please use he.config')
    es_url = urllib.parse.urlparse(es_url)

    aws_region = config_obj.get('region')
    if aws_region is None:
        raise HeliumException('No configured region. '
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
    """Set or read the Helium configuration

    To retrieve the current config, call directly, without arguments:
        >>> import helium as he
        >>> he.config()

    To trigger autoconfiguration, call with just the navigator URL:
        >>> he.config('https://example.com')

    To set config values, call with one or more key=value pairs:
        >>> he.config(navigator_url='http://example.com',
        ...           elastic_search_url='http://example.com/queries')
    When setting config values, unrecognized values are rejected.  Acceptable
    config values can be found in `helium.util.CONFIG_TEMPLATE`

    :param autoconfig_url: URL indicating a location to configure from
    :param **config_values: `key=value` pairs to set in the config
    """
    if autoconfig_url and config_values:
        raise HeliumException("Expected either an auto-config URL or key=value pairs, but got both.")
    # Total distinction of args and kwargs -- config(autoconfig_url='http://foo.com')
    if autoconfig_url and len(autoconfig_url) > 1:
        raise HeliumException("Expected a single autoconfig URL argument, not multiple args.")

    config_template = read_yaml(CONFIG_TEMPLATE)
    if autoconfig_url:
        autoconfig_url = autoconfig_url[0].rstrip('/')
        if not autoconfig_url[:7].lower() in ('http://', 'https:/'):
            autoconfig_url = 'https://' + autoconfig_url
        config_template['navigator_url'] = autoconfig_url  # set the provided navigator URL
        config_url = autoconfig_url + '/config.json'

        validate_url(config_url)

        # TODO: handle http basic auth via URL if using https (https://user:pass@hostname/path)
        response = requests.get(config_url)
        if not response.ok:
            message = "An HTTP Error ({code}) occurred: {reason}"
            raise HeliumException(
                message.format(code=response.status_code, reason=response.reason),
                response=response
                )
        new_config = read_yaml(response.text)  # handles JSON and YAML (YAML is a superset of JSON)

        for key, value in new_config.items():
            # No key validation, per current fast dev rate on config.json.
            # if key not in config_template:
            #     raise HeliumException("Unrecognized configuration key from {}: {}".format(config_url, key))
            if value and key.endswith('_url'):
                validate_url(value)
        # Use their config + our defaults, keeping their comments
        if yaml_has_comments(new_config):
            # add defaults for keys missing from their config
            for key in set(config_template) - set(new_config):
                new_config[key] = config_template[key]
            write_yaml(new_config, CONFIG_PATH, keep_backup=True)
            return new_config
        # Use our config + their configured values, keeping our comments.
        else:
            for key, value in new_config.items():
                config_template[key] = value
            write_yaml(config_template, CONFIG_PATH, keep_backup=True)
            return config_template
    # No autoconfig URL given -- use local config
    if CONFIG_PATH.exists():
        local_config = read_yaml(CONFIG_PATH)
    else:
        local_config = config_template

    for key, value in config_values.items():
        # No key validation, per current fast dev rate on config.json.
        # if key not in config_template:
        #     raise HeliumException("Unrecognized configuration key: {}".format(key))
        if value and key.endswith('_url'):
            validate_url(value)
        local_config[key] = value
    write_yaml(local_config, CONFIG_PATH, keep_backup=True)
    return local_config
