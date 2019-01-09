# Parameters for a new T4 stack

Once you have uploaded a template to CloudFormation, you will be prompted for several parameter values. This short guide will help you keep moving towards your own T4 stack.

## BucketDescription

This is a short explanation of your bucket that will be displayed alongside its icon and title in the dropdown menu at the top-left of the navigator.

## BucketIcon

This is a URL that points to a square icon that will display as part of your bucket's entry in the dropdown manu.

## BucketTitle

Title for your bucket in the dropdown menu.

## CertificateArn

This is the arn for your AWS-managed SSL certificate for your QuiltWebHost domain. Use AWS Certificate Manager to set this up.

## ConfigBucketName

An unused bucket name for the template to create and populate with your navigator's configuration.

## QuiltBucketName

The name of an existing S3 bucket you want to use with T4. It will store your T4 data.

## QuiltWebHost

The URL you want to use to access your navigator on the Internet. You must have a valid SSL certificate for this domain in `CertificateArn` if you want to use https.

## Users

A non-empty comma-separated list of IAM User ARNs that will grant permission to those users to search. A good first entry in this list is your own ARN, which you can find in IAM.


# Notes

Updating BucketIcon, BucketDescription, or BucketTitle will not update your navigator configuration -- these parameters are only checked when a stack is being created at this time. You'll need to update your federation.json in your config bucket to update these values.
