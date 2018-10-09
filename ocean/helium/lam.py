import boto3
from datetime import datetime
import json
import os
from botocore.vendored import requests
import sys

s3_client = boto3.client("s3")

es_url = 'https://search-test-public-nh4nbnm62agkzagkzmk745guz4.us-east-1.es.amazonaws.com/'
post_url = '{}{}'.format(es_url, 'drive/_doc')

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
    if len(meta_text_parts):
        meta_text = ' '.join(meta_text_parts)
    result = {
        'system_meta': helium,
        'user_meta': user_meta,
        'comment': comment,
        'target': target,
        'meta_text': meta_text
    }
    return result

def post_to_es(event_type, size, text, key, post_url, meta, version_id=''):
    headers = {'content-type': 'application/json'}
    data = {
        'type': event_type,
        'size': size,
        'text': text,
        'key': key,
        'updated': datetime.utcnow().isoformat(),
        'version_id': version_id
    }
    data = {**data, **transform_meta(meta)}
    r = requests.post(post_url, json=data, headers=headers)
    if r.status_code != 201:
        print('Exception when making request to ES')
        print(r.text)

def handler(event, context):
    for record in event['Records']:
        try:
            eventname = record['eventName']
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            if eventname == 'ObjectRemoved:Delete':
                event_type = 'Delete'
                post_to_es(event_type, 0, '', key, post_url, {})
                continue
            elif eventname == 'ObjectCreated:Put':
                event_type = 'Create'
            else:
                event_type = eventname
            response = s3_client.get_object(Bucket=bucket, Key=key)
            size = response['ContentLength']
            meta = response['Metadata']
            version_id = response['VersionId']
            text = ''
            if key.endswith('.md'):
                text = response['Body'].read().decode('utf-8')
            elif key.endswith('.json'):
                data = json.loads(response['Body'].read().decode('utf-8'))
                meta['json'] = data
            # TODO: more plaintext types here

            # decode helium metadata
            try:
                meta['helium'] = json.loads(meta['helium'])
            except:
                print('decoding helium metadata failed')
                pass

            post_to_es(event_type, size, text, key, post_url, meta, version_id)
        except Exception as e:
            # do our best to process each result
            print("Exception encountered")
            print(e)
            import traceback
            traceback.print_tb(e.__traceback__)
            pass
