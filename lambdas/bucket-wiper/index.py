#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import boto3
import cfnresponse


def lambda_handler(event, context):
    try:
        bucket = event['ResourceProperties']['BucketName']

        if event['RequestType'] == 'Delete':
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(bucket)
            # for obj_version in bucket.object_versions.all():
            versioned_objs = []
            for obj_version in bucket.object_versions.all():
                versioned_objs.append({'Key': obj_version.object_key,
                                       'VersionId': obj_version.id})
            bucket.delete_objects(Delete={'Objects': versioned_objs})
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except Exception as e:
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
