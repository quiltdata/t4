import json
import re
from six.moves import urllib
from urllib.parse import urlparse, unquote
import datetime
import pytz

from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection
import requests
import humanize

from .data_transfer import (copy_file, get_bytes, put_bytes, delete_object, list_objects,
                            list_object_versions, _update_credentials)
from .formats import FormatRegistry
from .packages import get_package_registry, Package
from .session import get_registry_url, get_session
from .util import (HeliumConfig, QuiltException, CONFIG_PATH,
                   CONFIG_TEMPLATE, fix_url, parse_file_url, parse_s3_url, read_yaml, validate_url,
                   write_yaml, yaml_has_comments, validate_package_name)

# backports
try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib


def copy(src, dest):
    """
    Copies ``src`` object from T4 to ``dest``.

    Either of ``src`` and ``dest`` may be S3 paths (starting with ``s3://``)
    or local file paths (starting with ``file:///``).

    Parameters:
        src (str): a path to retrieve
        dest (str): a path to write to
    """
    copy_file(fix_url(src), fix_url(dest))


def put(obj, dest, meta=None):
    """Write an in-memory object to the specified T4 ``dest``.

    Note:
        Does not work with all objects -- object must be serializable.

    You may pass a dict to ``meta`` to store it with ``obj`` at ``dest``.

    Parameters:
        obj: a serializable object
        dest (str): A URI
        meta (dict): Optional. metadata dict to store with ``obj`` at ``dest``
    """
    all_meta = {'user_meta': meta}
    clean_dest = fix_url(dest)
    ext = pathlib.PurePosixPath(unquote(urlparse(clean_dest).path)).suffix
    data, format_meta = FormatRegistry.serialize(obj, all_meta, ext)
    all_meta.update(format_meta)

    put_bytes(data, clean_dest, all_meta)


def get(src):
    """Retrieves src object from T4 and loads it into memory.

    An optional ``version`` may be specified.

    Parameters:
        src (str): A URI specifying the object to retrieve

    Returns:
        tuple: ``(data, metadata)``.  Does not work on all objects.
    """
    clean_src = fix_url(src)
    data, meta = get_bytes(clean_src)
    ext = pathlib.PurePosixPath(unquote(urlparse(clean_src).path)).suffix

    return FormatRegistry.deserialize(data, meta, ext=ext), meta.get('user_meta')


def _tophashes_with_packages(registry=None):
    """Return a dictionary of tophashes and their corresponding packages

    Parameters:
        registry (str): URI of the registry to enumerate

    Returns:
        dict: a dictionary of tophash keys and package name entries
    """
    registry_base_path = get_package_registry(fix_url(registry) if registry else None)
    registry_url = urlparse(registry_base_path)
    out = {}

    if registry_url.scheme == 'file':
        registry_dir = pathlib.Path(parse_file_url(registry_url))

        for pkg_namespace_path in (registry_dir / 'named_packages').iterdir():
            pkg_namespace = pkg_namespace_path.name

            for pkg_subname_path in pkg_namespace_path.iterdir():
                pkg_subname = pkg_subname_path.name
                pkg_name = pkg_namespace + '/' + pkg_subname

                package_timestamps = [ts.name for ts in pkg_subname_path.iterdir()
                                      if ts.name != 'latest']

                for timestamp in package_timestamps:
                    tophash = (pkg_namespace_path / pkg_subname / timestamp).read_text()
                    if tophash in out:
                        out[tophash].update({pkg_name})
                    else:
                        out[tophash] = {pkg_name}

    elif registry_url.scheme == 's3':
        bucket, path, version = parse_s3_url(registry_url)

        pkg_namespace_path = path + '/named_packages/'

        for pkg_entry in list_objects(bucket, pkg_namespace_path):
            pkg_entry_path = pkg_entry['Key']
            tophash, meta = get_bytes('s3://' + bucket + '/' + pkg_entry_path)
            tophash = tophash.decode('utf-8')
            pkg_name = "/".join(pkg_entry_path.split("/")[-3:-1])

            if tophash in out:
                out[tophash].update({pkg_name})
            else:
                out[tophash] = {pkg_name}

    else:
        raise NotImplementedError

    return out


def delete_package(name, registry=None):
    """
    Delete a package. Deletes only the manifest entries and not the underlying files.

    Parameters:
        name (str): Name of the package
        registry (str): The registry the package will be removed from
    """
    validate_package_name(name)

    if name not in list_packages(registry):
        raise QuiltException("No such package exists in the given directory.")

    registry_base_path = get_package_registry(fix_url(registry) if registry else None)
    registry_url = urlparse(registry_base_path)
    pkg_namespace, pkg_subname = name.split("/")

    tophashes_with_packages = _tophashes_with_packages(registry)

    if registry_url.scheme == 'file':

        registry_dir = pathlib.Path(parse_file_url(registry_url))
        pkg_namespace_dir = registry_dir / 'named_packages' / pkg_namespace
        pkg_dir = pkg_namespace_dir / pkg_subname
        packages_path = registry_dir / 'packages'

        for tophash_file in pkg_dir.iterdir():
            # skip latest, which always duplicates a tophashed file
            timestamp = tophash_file.name
            tophash = tophash_file.read_text()

            if timestamp != 'latest' and len(tophashes_with_packages[tophash]) == 1:
                (packages_path / tophash).unlink()

            tophash_file.unlink()

        pkg_dir.rmdir()

        if not list(pkg_namespace_dir.iterdir()):
            pkg_namespace_dir.rmdir()

    elif registry_url.scheme == 's3':
        bucket, path, version = parse_s3_url(registry_url)
        pkg_namespace_dir = path + '/named_packages/' + pkg_namespace
        pkg_dir = pkg_namespace_dir + '/' + pkg_subname + '/'
        packages_path = path + '/packages/'

        for tophash_obj_repr in list_objects(bucket, pkg_dir):
            tophash_file = tophash_obj_repr['Key']
            timestamp = tophash_file.split("/")[-1]
            tophash_path = 's3://' + bucket + '/' + tophash_file
            tophash, meta = get_bytes(tophash_path)
            tophash = tophash.decode('utf-8')

            if timestamp != 'latest' and len(tophashes_with_packages[tophash]) == 1:
                delete_object(bucket, packages_path + tophash)

            delete_object(bucket, tophash_file)

    else:
        raise NotImplementedError


def list_packages(registry=None):
    """ Lists Packages in the registry.

    Returns a list of all named packages in a registry.
    If the registry is None, default to the local registry.

    Args:
        registry(string): location of registry to load package from.

    Returns:
        A list of strings containing the names of the packages
    """
    class PackageList:
        """Display wrapper for list_packages"""

        def __init__(self, pkg_info):
            self.pkg_names = [info['pkg_name'].replace(':latest', '') for info in pkg_info]
            self._repr = self.create_str(pkg_info)

        def __repr__(self):
            return self._repr

        def __iter__(self):
            return iter(self.pkg_names)

        def __len__(self):
            return len(self.pkg_names)

        def __contains__(self, item):
            return item in self.pkg_names

        @staticmethod
        def _fmt_str(string, strlen):
            """Formats strings to a certain width"""
            if len(string) > strlen - 1:
                return string[:strlen - 1] + '…'
            else:
                return string.ljust(strlen)

        def create_str(self, pkg_info):
            """Generates a human-readable string representation of a registry"""
            if pkg_info:
                pkg_name_display_width = max(max([len(info['pkg_name']) for info in pkg_info]), 27)
            else:
                pkg_name_display_width = 27

            out = (f"{self._fmt_str('PACKAGE', pkg_name_display_width)}\t"
                   f"{self._fmt_str('TOPHASH', 12)}\t"
                   f"{self._fmt_str('CREATED', 12)}\t"
                   f"{self._fmt_str('SIZE', 12)}\t"
                   f"\n")
            for pkg_dict in pkg_info:
                tdelta = datetime.datetime.now(pytz.utc) -\
                    datetime.datetime.fromtimestamp(int(pkg_dict['ctime']), pytz.utc)
                tdelta_str = humanize.naturaltime(tdelta)
                size_str = humanize.naturalsize(pkg_dict['size'])

                out += (f"{self._fmt_str(pkg_dict['pkg_name'], pkg_name_display_width)}\t"
                        f"{self._fmt_str(pkg_dict['top_hash'][:12], 15)}\t"
                        f"{self._fmt_str(tdelta_str, 15)}\t"
                        f"{self._fmt_str(size_str, 15).rstrip(' ')}\t\n")
            return out

    base_registry = get_package_registry(fix_url(registry) if registry else None)
    named_packages = base_registry + '/named_packages'

    pkg_info = []

    registry_url = urlparse(named_packages)
    if registry_url.scheme == 'file':
        registry_dir = pathlib.Path(parse_file_url(registry_url))

        for named_path in registry_dir.glob('*/*'):
            name = named_path.relative_to(registry_dir).as_posix()

            pkg_hashes = []
            pkg_sizes = []
            pkg_ctimes = []
            pkg_name = name

            with open(named_path / 'latest', 'r') as latest_hash_file:
                latest_hash = latest_hash_file.read()

            for pkg_hash_path in named_path.rglob('*/'):
                if pkg_hash_path.name == 'latest':
                    continue

                with open(pkg_hash_path, 'r') as pkg_hash_file:
                    pkg_hash = pkg_hash_file.read()
                    pkg_hashes.append(pkg_hash)

                if pkg_hash == latest_hash:
                    pkg_name = f'{pkg_name}:latest'

                pkg_ctimes.append(pkg_hash_path.stat().st_ctime)

                pkg = Package.browse(name, registry='local', top_hash=pkg_hash)
                pkg_sizes.append(pkg.reduce(lambda tot, tup: tot + tup[1].size, default=0))

            for top_hash, ctime, size in zip(pkg_hashes, pkg_ctimes, pkg_sizes):
                pkg_info.append(
                    {'pkg_name': pkg_name, 'top_hash': top_hash, 'ctime': ctime, 'size': size}
                )

    elif registry_url.scheme == 's3':
        bucket_name, bucket_registry_path, _ = parse_s3_url(registry_url)
        bucket_registry_path = bucket_registry_path + '/'

        pkg_namespaces, _ = list_objects(bucket_name, bucket_registry_path, recursive=False)
        pkg_namespaces = [result['Prefix'] for result in pkg_namespaces]

        # go through package namespaces to get packages
        for pkg_namespace in pkg_namespaces:
            pkg_names, _ = list_objects(
                bucket_name,
                pkg_namespace,
                recursive=False
            )
            pkg_names = [pkg_name['Prefix'] for pkg_name in pkg_names]

            # go through packages to get package hash files
            for pkg_name in pkg_names:
                pkg_hashes = []
                pkg_sizes = []
                pkg_ctimes = []
                pkg_names = []

                _, pkg_hashfiles = list_objects(
                    bucket_name,
                    pkg_name,
                    recursive=False
                )

                latest_hashfile = next(hf for hf in pkg_hashfiles if '/latest' in hf['Key'])['Key']
                latest_hashfile_fullpath = f's3://{bucket_name}/{latest_hashfile}'
                latest_hash, _ = get_bytes(latest_hashfile_fullpath)
                latest_hash = latest_hash.decode()

                # go through package hashfiles to get manifest files
                pkg_hash_paths = []
                for pkg_hashfile in pkg_hashfiles:
                    pkg_hashfile_key = pkg_hashfile['Key']

                    if pkg_hashfile_key.split('/')[-1] == 'latest':
                        continue

                    pkg_hash, _ = get_bytes(f's3://{bucket_name}/{pkg_hashfile_key}')
                    pkg_hash = pkg_hash.decode()

                    pkg_last_modified = pkg_hashfile['LastModified'].timestamp()
                    pkg_hash_paths.append(pkg_hashfile_key)
                    pkg_ctimes.append(pkg_last_modified)

                # go through manifest files to get package info
                for pkg_hash_path in pkg_hash_paths:
                    name = pkg_name[len(bucket_registry_path):].strip('/')

                    pkg_hash, _ = get_bytes('s3://' + bucket_name + '/' + pkg_hash_path)
                    pkg_hash = pkg_hash.decode()

                    if pkg_hash == latest_hash:
                        pkg_name = name + ':latest'
                    else:
                        pkg_name = name

                    pkg_names.append(pkg_name)
                    pkg_hashes.append(pkg_hash)

                    pkg = Package.browse(
                        pkg_name, top_hash=pkg_hash, registry='s3://' + bucket_name
                    )
                    pkg_sizes.append(pkg.reduce(lambda tot, tup: tot + tup[1].size, default=0))

                for top_hash, ctime, size in zip(pkg_hashes, pkg_ctimes, pkg_sizes):
                    pkg_info.append(
                        {'pkg_name': pkg_name, 'top_hash': top_hash, 'ctime': ctime, 'size': size}
                    )

    else:
        raise NotImplementedError

    def sorter(pkg_info):
        pkg_name, pkg_cdate = pkg_info['pkg_name'], pkg_info['ctime']
        is_latest = ':latest' in pkg_name
        pkg_realname = pkg_name.replace(':latest', '')
        return (pkg_realname, not is_latest, -pkg_cdate)

    pkg_info = sorted(pkg_info, key=sorter)
    return PackageList(pkg_info)


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
    """Set or read the T4 configuration.

    To retrieve the current config, call directly, without arguments:

        >>> import t4
        >>> t4.config()

    To trigger autoconfiguration, call with just the navigator URL:

        >>> t4.config('https://example.com')

    To set config values, call with one or more key=value pairs:

        >>> t4.config(navigator_url='http://example.com',
        ...           elastic_search_url='http://example.com/queries')

    When setting config values, unrecognized values are rejected.  Acceptable
    config values can be found in `t4.util.CONFIG_TEMPLATE`.

    Args:
        autoconfig_url: A (single) URL indicating a location to configure from
        **config_values: `key=value` pairs to set in the config

    Returns:
        HeliumConfig: (an ordered Mapping)
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
