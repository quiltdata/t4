import boto3
import botocore
import cfnresponse

s3_client = boto3.client('s3')

def handler(event, context):
    if event['RequestType'] == 'Delete':
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return

    try:
        props = event['ResourceProperties']
        bucket = props['Bucket']
        catalog_host = props['QuiltWebHost']
        enable_versioning(bucket)
        set_cors(bucket, catalog_host)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return
    except Exception as e:
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        raise

def enable_versioning(bucket):
    s3_client.put_bucket_versioning(
            Bucket=bucket,
            VersioningConfiguration={
                'Status': 'Enabled'
            }
        )

def set_cors(bucket, catalog_host):
    new_cors_rule = {
        'AllowedHeaders': [ '*' ],
        'AllowedMethods': [
            'GET',
            'HEAD',
            'PUT',
            'POST'
        ],
        'AllowedOrigins': [
            'https://' + catalog_host
        ],
        'ExposeHeaders': [
            'Content-Length',
            'x-amz-meta-helium'
        ],
        'MaxAgeSeconds': 3000
    }
            
    try:
        existing_cors_rules = s3_client.get_bucket_cors(Bucket=bucket)['CORSRules']
    # if there's no CORS set at all, we'll get an error
    except botocore.exceptions.ClientError as problem:
        print(problem) # goes to CloudWatch
        existing_cors_rules = []

    if new_cors_rule not in existing_cors_rules:
        existing_cors_rules.append(new_cors_rule)
        s3_client.put_bucket_cors(
            Bucket=bucket,
            CORSConfiguration={
                'CORSRules': existing_cors_rules
            }
        )
