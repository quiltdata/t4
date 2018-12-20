from datetime import datetime
import json
import os
from urllib.parse import unquote

from aws_requests_auth.aws_auth import AWSRequestsAuth
import botocore
import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
import nbformat

DEFAULT_CONFIG = {
    'md': True,
    'json': True,
    'ipynb': True,
}

NB_VERSION = 4 # default notebook version for nbformat

S3_CLIENT = boto3.client("s3")

def get_config(bucket):
    try:
        loaded_object = S3_CLIENT.get_object(Bucket=bucket, Key='.quilt/config.json')
        loaded_config = json.load(loaded_object['Body'])
        return {**DEFAULT_CONFIG, **loaded_config}
    except botocore.exceptions.ClientError:
        return DEFAULT_CONFIG
    except Exception as e:
        print('Exception when getting config')
        print(e)
        import traceback
        traceback.print_tb(e.__traceback__)

        return DEFAULT_CONFIG

def transform_meta(meta):
    ''' Reshapes metadata for indexing in ES '''
    helium = meta.get('helium')
    user_meta = {}
    comment = ''
    target = ''
    meta_text = ''
    if helium:
        user_meta = helium.pop('user_meta', {})
        comment = helium.pop('comment', '') or ''
        target = helium.pop('target', '') or ''
    meta_text_parts = [comment, target]
    if helium:
        meta_text_parts.append(json.dumps(helium))
    if user_meta:
        meta_text_parts.append(json.dumps(user_meta))
    if meta_text_parts:
        meta_text = ' '.join(meta_text_parts)
    result = {
        'system_meta': helium,
        'user_meta': user_meta,
        'comment': comment,
        'target': target,
        'meta_text': meta_text
    }
    return result

def extract_text(notebook_str):
    """ Extract code and markdown
    Args:
        * nb - notebook as a string
    Returns:
        * str - select code and markdown source (and outputs)
    Pre:
        * notebook is well-formed per notebook version 4
        * 'cell_type' is defined for all cells
        * 'source' defined for all 'code' and 'markdown' cells
    Throws:
        * Anything nbformat.reads() can throw :( which is diverse and poorly
        documented, hence the `except Exception` in handler()
    Notes:
        * Deliberately decided not to index output streams and display strings
        because they were noisy and low value
        * Tested this code against ~6400 Jupyter notebooks in
        https://alpha.quiltdata.com/b/alpha-quilt-storage/tree/notebook-search/
        * Might be useful to index "cell_type" : "raw" in the future
    See also:
        * Format reference https://nbformat.readthedocs.io/en/latest/format_description.html
    """
    formatted = nbformat.reads(notebook_str, as_version=NB_VERSION)
    # prevent common error after calling nbformat: missing 'source' key
    cells = [c for c in formatted.get('cells', []) 
             if 'source' in c and 'cell_type' in c]
    code = [c['source'] for c in cells if c['cell_type'] == 'code']
    markdown = [m['source'] for m in cells if m['cell_type'] == 'markdown']

    return '\n'.join(code + markdown)

def post_to_es(event_type, size, text, key, meta, version_id=''):

    ES_URL = os.environ['ES_URL']
    ES_HOST = ES_URL.lstrip('https://')
    ES_INDEX = 'drive'

    data = {
        'type': event_type,
        'size': size,
        'text': text,
        'key': key,
        'updated': datetime.utcnow().isoformat(),
        'version_id': version_id
    }
    data = {**data, **transform_meta(meta)}
    data['meta_text'] = ' '.join([data['meta_text'], key])
    try:
        session = boto3.session.Session()
        awsauth = AWSRequestsAuth(
            aws_access_key=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            aws_token=os.environ['AWS_SESSION_TOKEN'],
            aws_host=ES_HOST,
            aws_region=session.region_name,
            aws_service='es'
        )

        es = Elasticsearch(
            hosts=[{'host': ES_HOST, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )

        res = es.index(index=ES_INDEX, doc_type='_doc', body=data)
        print(res)
    except Exception as e:
        print("Exception encountered when POSTing to ES")
        print(e)
        import traceback
        traceback.print_tb(e.__traceback__)

def handler(event, context):
    for record in event['Records']:
        try:
            eventname = record['eventName']
            bucket = unquote(record['s3']['bucket']['name'])
            key = unquote(record['s3']['object']['key'])
            config = get_config(bucket)
            if eventname == 'ObjectRemoved:Delete':
                event_type = 'Delete'
                post_to_es(event_type, 0, '', key, {})
                continue
            elif eventname == 'ObjectCreated:Put':
                event_type = 'Create'
            else:
                event_type = eventname
            try:
                response = S3_CLIENT.get_object(Bucket=bucket, Key=key)
            except botocore.exceptions.ClientError as e:
                print("Exception while getting object")
                print(e)
                print(bucket)
                print(key)
                raise

            size = response['ContentLength']
            meta = response['Metadata']
            version_id = response['VersionId']
            text = ''
            if key.endswith('.md') and config['md']:
                try:
                    text = response['Body'].read().decode('utf-8')
                except UnicodeDecodeError:
                    print("Unicode decode error in .md file")
            elif key.endswith('.ipynb') and config['ipynb']:
                try:
                    notebook = json.load(response['Body'])
                    text = extract_text(notebook)
                except (json.JSONDecodeError, nbformat.reader.NotJSONError):
                    print("Invalid JSON in {}.".format(key))
                except (KeyError, AttributeError)  as err:
                    print("Missing key in {}: {}".format(key, err))
                # there might be more errors than covered by test_read_notebook
                # better not to fail altogether
                except Exception as exc:#pylint: disable=broad-except
                    print("Exception in file {}: {}".format(key, exc))
            # TODO: more plaintext types here
            # decode helium metadata
            try:
                meta['helium'] = json.loads(meta['helium'])
            except (KeyError, json.JSONDecodeError):
                print('decoding helium metadata failed')

            post_to_es(event_type, size, text, key, meta, version_id)
        except Exception as e:
            # do our best to process each result
            print("Exception encountered")
            print(e)
            import traceback
            traceback.print_tb(e.__traceback__)
