"""
navigator-config

Initializes and updates catalog config files
"""
import json
import os
from pathlib import Path

import boto3
import cfnresponse
from jsonschema import Draft4Validator, ValidationError

S3_CLIENT = boto3.client('s3')

def handler(event, context):
    """
    top-level handler for CloudFormation custom resource protocol
    """
    if event['RequestType'] == 'Delete':
        try:
            stackname = event['ResourceProperties']['StackName']
            cf_client = boto3.client('cloudformation')
            describe = cf_client.describe_stacks(StackName=stackname)
            status = describe['Stacks'][0]['StackStatus']

            if not status == 'DELETE_IN_PROGRESS':
                # If stack isn't deleting, then this resource is just getting cleaned
                #   up -- so do nothing
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
                return

            wipe_bucket(event, context)
            return
        except Exception:
            cfnresponse.send(event, context, cfnresponse.FAILED, {})
            raise

    # event['RequestType'] in ['Create', 'Update']
    try:
        props = event['ResourceProperties']

        catalog_config = props['CatalogConfig']
        federation = props['Federation']
        
        config_bucket = props['DestBucket']
        config_dir = props['DestDir']

        validate_configs(catalog_config, federation)

        S3_CLIENT.put_object(
            ACL='public-read',
            Body=federation,
            Bucket=config_bucket,
            Key=config_dir + 'federation.json',
            ContentType='application/json'
        )

        S3_CLIENT.put_object(
            ACL='public-read',
            Body=catalog_config,
            Bucket=config_bucket,
            Key=config_dir + 'config.json',
            ContentType='application/json'
        )

        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception:
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
        raise

def wipe_bucket(event, context):
    """
    Removes all versions of `config.json` and `federation.json` from
        the config bucket. Called on stack delete.
    """
    try:
        bucket = event['ResourceProperties']['DestBucket']

        if event['RequestType'] == 'Delete':
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(bucket)
            # for obj_version in bucket.object_versions.all():
            versioned_objs = []

            files_to_delete = ['config.json', 'federation.json']
            for prefix in files_to_delete:
                for obj_version in bucket.object_versions.filter(Prefix=prefix):
                    versioned_objs.append({'Key': obj_version.object_key,
                                           'VersionId': obj_version.id})

            # Use a list comprehension to break into chunks of size 1000
            # for API limits.
            n = 1000
            for shard in [versioned_objs[i * n:(i + 1) * n] \
                for i in range((len(versioned_objs) + n - 1) // n )]:
                bucket.delete_objects(Delete={'Objects': shard})
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})

def validate_configs(catalog_config, federation):
    """
    Catches bad configs. Throws if configs don't match schema.
    """
    lambda_root = Path(os.environ['LAMBDA_TASK_ROOT'])
    catalog_schema_path = lambda_root / 'config-schema.json'
    with open(catalog_schema_path) as schema:
        VALIDATOR = Draft4Validator(json.load(schema))
        VALIDATOR.validate(json.loads(catalog_config))

    federation_schema_path = lambda_root / 'federation-schema.json'
    with open(federation_schema_path) as schema:
        VALIDATOR = Draft4Validator(json.load(schema))
        VALIDATOR.validate(json.loads(federation))
