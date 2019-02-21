"""
search_util.py

Contains search-related glue code
"""
import json
from urllib.parse import urlparse

from aws_requests_auth.boto_utils import BotoAWSRequestsAuth
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
                               aws_secret_key=creds.secret_key,
                               aws_host=es_url.hostname,
                               aws_region=aws_region,
                               aws_service='es')
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
