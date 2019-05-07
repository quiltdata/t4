"""
Set up indexer notification on data bucket.

Remove notification on delete.
"""
import boto3

from t4_lambda_shared.cfnresponse import send, SUCCESS, FAILED

def set_mappings(params, *, delete=False):
    """ Sets up desired mappings after checking no mappings currently exist. """
    s3 = boto3.client('s3')
    if delete:
        # clear notifications
        params['NotificationConfiguration'] = {}
        s3.put_bucket_notification_configuration(**params)
        return

    existing = s3.get_bucket_notification_configuration(Bucket=params['Bucket'])
    if 'TopicConfigurations' in existing \
            or 'QueueConfigurations' in existing \
            or 'LambdaFunctionConfigurations' in existing:
        raise Exception('Unable to attach notifications. Notification already configured '
                'on bucket {}.'.format(params['Bucket']))

    s3.put_bucket_notification_configuration(**params)

def select_params(params):
    """ Grabs just the necessary keys from params """
    return {
        'Bucket': params['Bucket'],
        'NotificationConfiguration': params['NotificationConfiguration']
    }

def handler(event, context):
    """ Top-level handler for custom resource """
    print('Changing bucket notification settings')
    try:
        params = select_params(event['ResourceProperties'])
        bucket = params['Bucket']
        current_resource_id = 'notification_' + bucket
        if event['RequestType'] == 'Create':
            set_mappings(params)
            send(event, context, SUCCESS, physical_resource_id=current_resource_id)
            return
        elif event['RequestType'] == 'Update':
            if event['PhysicalResourceId'] == current_resource_id:
                # do nothing if physical_resource_id is unchanged
                send(event, context, SUCCESS, physical_resource_id=current_resource_id)
                return
            # Otherwise, bucket name changed. Must set up new notification.
            set_mappings(params)
            # Also must delete old notification on old bucket.
            old_params = select_params(event['OldResourceProperties'])
            set_mappings(old_params, delete=True)
            # report success with new resource id
            send(event, context, SUCCESS, physical_resource_id=current_resource_id)
            return
        elif event['RequestType'] == 'Delete':
            # We don't have access to OldResourceProperties here, so we
            # can't do anything helpful. So we do nothing.
            send(event, context, SUCCESS, physical_resource_id=current_resource_id)
            return
        else:
            # unknown event type
            send(event, context, FAILED, physical_resource_id=current_resource_id,
                    reason='Unknown event type ' + event['RequestType'])
            return

    except Exception as e:
        print('Exception encountered')
        print(str(e))
        print(str(event))
        # TODO: send failure with error message
        send(event, context, FAILED, reason=str(e))
        raise
