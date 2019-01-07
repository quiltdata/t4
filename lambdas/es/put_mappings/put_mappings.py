import os

from aws_requests_auth.aws_auth import AWSRequestsAuth
import boto3
import cfnresponse
from elasticsearch import Elasticsearch, RequestsHttpConnection

ES_INDEX = 'drive'

def handler(event, context):
    try:
        es_host = event['ResourceProperties']['ES_HOST']
        session = boto3.session.Session()

        mappings = {
            'mappings': {
                '_doc': {
                    'properties': {
                        'updated': {
                            'type': 'date'
                        },
                        'comment': {
                            'type': 'text'
                        },
                        'target': {
                            'type': 'keyword'
                        },
                        'version_id': {
                            'type': 'text',
                            'copy_to': 'content'
                        },
                        'size': {
                            'type': 'long',
                            'copy_to': 'content'
                        },
                        'text': {
                            'type': 'text',
                            'copy_to': 'content'
                        },
                        'type': {
                            'type': 'text',
                            'copy_to': 'content'
                        },
                        'key': {
                            'type': 'keyword',
                        },
                        'meta': {
                            'type': 'object'
                        },
                        'meta_text': {
                            'type': 'text',
                            'copy_to': 'content'
                        },
                        'system_meta': {
                            'type': 'object'
                        },
                        'content': {
                            'type': 'text'
                        }
                    }
                }
            }
        }

        awsauth = AWSRequestsAuth(
            aws_access_key=os.environ['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
            aws_token=os.environ['AWS_SESSION_TOKEN'],
            aws_host=es_host,
            aws_region=session.region_name,
            aws_service='es'
        )

        es = Elasticsearch(
            hosts=[{'host': es_host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )

        es.indices.create(index=ES_INDEX, body=mappings)

        del event['ResourceProperties']['ServiceToken']

        cfnresponse.send(event,
                         context,
                         cfnresponse.SUCCESS, {})
    except:
        cfnresponse.send(event,
                         context,
                         cfnresponse.FAILED, {})
        raise
