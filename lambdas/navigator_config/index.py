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
        config(props['DestBucket'], props['DestDir'], props['ConfigEsUrl'], props['ConfigApiUrl'], props['ConfigS3Bucket'])
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        raise

def config(dest_bucket, dest_dir, es_url, api_url, s3_bucket):
    region = boto3.session.Session().region_name

    config = dict(
        region=region,
        elastic_search_url=es_url,
        api_gateway_url=api_url
    )

    s3_client.put_object(
        ACL='public-read',
        Body=json.dumps(config),
        Bucket=dest_bucket,
        Key=dest_dir + 'config.json',
        ContentType='application/json'
    )

    js_config = dict(
        alwaysRequiresAuth=True,
        api="N/A",
        aws=dict(
            region=region,
            s3Bucket=s3_bucket,
            apiGatewayUrl=api_url,
            elasticSearchUrl=es_url,
        )
    )

    s3_client.put_object(
        ACL='public-read',
        Body="window.__CONFIG = %s;\n" % json.dumps(js_config),
        Bucket=dest_bucket,
        Key=dest_dir + 'config.js',
        ContentType='application/javascript'
    )
