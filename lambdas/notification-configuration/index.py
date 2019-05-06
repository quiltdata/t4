"""
Set up indexer notification on data bucket.

Remove notification on delete.
"""
import boto3

from t4_lambda_shared.cfnresponse import send, SUCCESS, FAILED

def create_mappings(params):
    """ Sets up desired mappings after checking no mappings currently exist. """
    s3 = boto3.client('s3')
    existing = s3.get_bucket_notification_configuration(Bucket=params['Bucket'])
    if existing['TopicConfigurations'] \
            or existing['QueueConfigurations'] \
            or existing['LambdaFunctionConfigurations']:
        raise Exception('Unable to attach notifications. Notification already configured '
                'on bucket {}.'.format(params['Bucket']))

    s3.put_bucket_notification_configuration(**params)
    return

def handler(event, context):
    print('Changing bucket notification settings')
    try:
        params = dict(event['ResourceProperties'])
        del params['ServiceToken']
        bucket = params['Bucket']
        current_resource_id = 'notification_' + bucket
        if event['RequestType'] == 'Create':
            create_mappings(params)
            send(event, context, SUCCESS, {}, physical_resource_id=current_resource_id)
            return
        elif event['RequestType'] == 'Update':
            if event['PhysicalResourceId'] == current_resource_id:
                # do nothing if physical_resource_id is unchanged
                send(event, context, SUCCESS, {}, physical_resource_id=current_resource_id)
                return
            # Otherwise, bucket name changed. Must set up new notification.
            # Also must delete old notification on old bucket.
            create_mappings(params)
            # delete old notification
            params = dict(event['OldResourceProperties'])
            del params['ServiceToken']
            params['NotificationConfiguration'] = {}
            s3.put_bucket_notification_configuration(**params)
            # report success with new resource id
            send(event, context, SUCCESS, {}, physical_resource_id=current_resource_id)
            return
        elif event['RequestType'] == 'Delete':
            # do nothing
            send(event, context, SUCCESS, {}, physical_resource_id=current_resource_id)
            return
        else:
            # unknown event type
            send(event, context, FAILED, {}, physical_resource_id=current_resource_id,
                    reason='Unknown event type ' + event['RequestType'])
            return

    except Exception as e:
        print('Exception encountered')
        print(str(e))
        # TODO: send failure with error message
        send(event, context, FAILED, {}, reason=str(e))
        raise
