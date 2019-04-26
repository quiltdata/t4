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
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        return

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
