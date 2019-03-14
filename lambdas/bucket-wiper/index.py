import boto3
import cfnresponse


def handler(event, context):
    try:
        bucket = event['ResourceProperties']['BucketName']

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
