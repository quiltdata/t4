"""
search_util.py

Contains search-related glue code
"""
import json
from urllib.parse import urlparse

from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
from aws_requests_auth.aws_auth import AWSRequestsAuth
from elasticsearch import Elasticsearch, RequestsHttpConnection

from .session import get_credentials
from .util import QuiltException

ES_INDEX = 'drive'

def _create_es(search_endpoint, aws_region):
    """
    search_endpoint: url for search endpoint
    aws_region: name of aws region endpoint is hosted in
    """
    es_url = urlparse(search_endpoint)

    credentials = get_credentials()
    if credentials:
        # use registry-provided credentials
        creds = credentials.get_frozen_credentials()
        auth = AWSRequestsAuth(aws_access_key=creds.access_key,
                               aws_secret_access_key=creds.secret_key,
                               aws_host=es_url.hostname,
                               aws_region=aws_region,
                               aws_service='es',
                               aws_token=creds.token,
                               )
    else:
        auth = BotoAWSRequestsAuth(aws_host=es_url.hostname,
                                   aws_region=aws_region,
                                   aws_service='es')

    port = es_url.port or (443 if es_url.scheme == 'https' else 80)

    es_client = Elasticsearch(
        hosts=[{'host': es_url.hostname, 'port': port}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    return es_client

def search(query, search_endpoint, limit, aws_region='us-east-1'):
    """
    Searches your bucket. Query may contain plaintext and clauses of the 
        form $key:"$value" that search for exact matches on specific keys.

    Arguments:
        query(string): query string
        search_endpoint(string): where to go to make the search
        limit(number): maximum number of results to return
        aws_region(string): aws region (used to sign requests)

    Returns either the request object (in case of an error)
            or a list of objects with the following keys:
        key: key of the object
        version_id: version_id of object version
        operation: Create or Delete
        meta: metadata attached to object
        size: size of object in bytes
        text: indexed text of object
        source: source document for object (what is actually stored in ElasticSeach)
        time: timestamp for operation
    """
    es_client = _create_es(search_endpoint, aws_region)

    payload = {'query': {'query_string': {
        'default_field': 'content',
        'query': query,
        'quote_analyzer': 'keyword',
        }}}

    if limit:
        payload['size'] = limit

    raw_response = es_client.search(index=ES_INDEX, body=payload)

    try:
        results = []
        for result in raw_response['hits']['hits']:
            key = result['_source']['key']
            vid = result['_source']['version_id']
            operation = result['_source']['type']
            meta = json.dumps(result['_source']['user_meta'])
            size = str(result['_source']['size'])
            text = result['_source']['text']

            time = str(result['_source']['updated'])
            results.append({
                'key': key,
                'version_id': vid,
                'operation': operation,
                'meta': meta,
                'size': size,
                'text': text,
                'source': result['_source'],
                'time': time
            })
        results = list(sorted(results, key=lambda x: x['time'], reverse=True))
        return results
    except KeyError:
        exception =  QuiltException("Query failed unexpectedly due to either a "
                                    "bad query or a misconfigured search service.")
        setattr(exception, 'raw_response', raw_response)
        raise exception

def get_raw_mapping(endpoint, aws_region):
    es_client = _create_es(endpoint, aws_region)
    raw_response = es_client.indices.get_mapping(index=ES_INDEX)
    return raw_response

def unpack_t4_meta(meta):
    """
    returns transformed meta object
    """
    if not meta:
        return {}
    user_meta = meta.pop('user_meta', {})
    comment = meta.pop('comment', '')
    target = meta.pop('target', '')
    return {
        'comment': comment,
        'target': target,
        'user_meta': user_meta,
        'system_meta': meta
    }

def unpack_mappings(mappings, field):
    """
    Takes mappings and unpacked field (list of parts), returns field type

    raises KeyError if field isn't present
    """
    mappings = mappings[ES_INDEX]['mappings']['_doc']
    properties = mappings['properties']

    last = field.pop()
    for field_part in field:
        properties = properties[field_part]
        if 'properties' in properties.keys():
            properties = properties['properties']

    current = properties[last]
    if 'properties' in current.keys():
        return 'object'

    return properties[last]['type']

def check_against_mappings(*, search_endpoint, aws_region, meta):
    """
    Checks to see whether uploading an object with `meta` will result in an indexer failure.
    Args (all keyword):
        search_endpoint: ES cluster to target
        aws_region: region of ES cluster
        meta: un-transformed T4 meta to check
    """
    transformed = unpack_t4_meta(meta)
    mappings = get_raw_mapping(search_endpoint, aws_region)
    def check_mapping_rec(current, meta_fragment):
        if isinstance(meta_fragment, dict):
            mapping_type = unpack_mappings(mappings, current)
            if mapping_type != 'object':
                raise QuiltException('Dict provided but search schema expects a {}'
                                     .format(mapping_type))
            for key in meta_fragment.keys():
                check_mapping_rec(current + [key], meta_fragment[key])
        elif isinstance(meta_fragment, int):
            mapping_type = unpack_mappings(mappings, current)
            if mapping_type not in ['long', 'float', 'double']:
                raise QuiltException('Number provided when search schema expects a {}'
                                     .format(mapping_type))
        elif isinstance(meta_fragment, float):
            mapping_type = unpack_mappings(mappings, current)
            if mapping_type not in ['long', 'float']:
                raise QuiltException('Float provided when search schema expects a {}'
                                     .format(mapping_type))
        elif isinstance(meta_fragment, str):
            mapping_type = unpack_mappings(mappings, current)
            if mapping_type == 'long':
                try:
                    float(meta_fragment)
                except ValueError:
                    raise QuiltException('Search schema requires a number for field {}'
                                         .format('.'.join(current)))
            elif mapping_type == 'date':
                # TODO: check if item is really a date
                pass
            elif mapping_type in ['keyword', 'text']:
                pass
            else:
                raise QuiltException('Metadata does not match search schema')

    check_mapping_rec([], transformed)
