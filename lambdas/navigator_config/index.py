import json

import boto3
import cfnresponse

s3_client = boto3.client('s3')

def handler(event, context):
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return

    try:
        props = event['ResourceProperties']
        config(props['DestBucket'], props['DestDir'], props['ConfigEsUrl'],
               props['ConfigApiUrl'], props['ConfigS3Bucket'],
               props['BucketTitle'], props['BucketIcon'], props['BucketDescription'])
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        raise

def config(dest_bucket, dest_dir, es_url, api_url, s3_bucket,
           bucket_title, bucket_icon, bucket_description):
    region = boto3.session.Session().region_name

    # test whether bucket is empty
    objects = s3_client.list_objects_v2(Bucket=dest_bucket, MaxKeys=1)
    if objects['KeyCount']:
        # exit early if bucket already has objects -- 
        #   don't want to overwrite existing configs
        return

    bucket_config = {
        'name': s3_bucket,
        'title': bucket_title,
        'icon': bucket_icon,
        'description': bucket_description,
        'searchEndpoint': es_url,
        'apiGatewayEndpoint': api_url,
        'region': region
    }

    federation = {
        'buckets': [
            bucket_config
        ]
    }

    s3_client.put_object(
        ACL='public-read',
        Body=json.dumps(federation),
        Bucket=dest_bucket,
        Key=dest_dir + 'federation.json',
        ContentType='application/json'
    )

    catalog_config = {
        'federations': [
            '/federation.json'
        ],
        'suggestedBuckets': [
            s3_bucket
        ],
        'apiGatewayEndpoint': api_url,
        'sentryDSN': '',
        'alwaysRequiresAuth': True,
        'defaultBucket': s3_bucket,
        'guestCredentials': {
            'accessKeyId': '',
            'secretAccessKey': ''
        },
        'signInRedirect': '/',
        'signOutRedirect': '/'
    }

    s3_client.put_object(
        ACL='public-read',
        Body=json.dumps(catalog_config),
        Bucket=dest_bucket,
        Key=dest_dir + 'config.json',
        ContentType='application/json'
    )
