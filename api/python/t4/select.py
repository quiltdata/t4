"""
Wrap  s3.select_object_content
"""

import boto3

from .util import split_path

s3 = boto3.client('s3')

# TODO: use fully qualified paths, check for the S3 scheme etc.
def select(fullpath, **kwargs):
    """Invokes S3 select on the indicated path
    Args:
        fullpath (str): full path to an S3 object
        kwargs (dict): passed through to boto3.select_object_content
    
    Returns:
        Selected content
    
    See also: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html?highlight=select#S3.Client.select_object_content
    """
    bucket, path = split_path(fullpath, require_subpath=True)