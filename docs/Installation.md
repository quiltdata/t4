T4 has two different components:
* A Python package, `t4`, distributed via `pip`
* A web interface, the T4 Catalog, deployed using [AWS CloudFormation](https://aws.amazon.com/cloudformation/)

If you have an already-provisioned catalog, only the Python package is needed.


## Installing the Python package

T4 is currently in pre-release alpha. To install the current T4 `master`, first ensure that you are in a Python 3.6 environment, then run:

```bash
$ pip install git+https://github.com/quiltdata/t4.git#subdirectory=api/python
```

In order to interface with a remote catalog you will also need valid AWS credentials. If this is your first time using AWS, ensure that you have the AWS CLI installed (`pip install aws-cli`), then run the following to store the IAM credentials you wish to use with T4:

```bash
$ aws configure
```

If you are already using AWS IAM you may reuse your credentials for T4. Alternatively you can create a Quilt-specific [profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-multiple-profiles.html).


## Deploying the catalog
The following instructions use CloudFormation to install T4 on a bucket in your AWS account.

* Log in to your AWS console

* Go to Services > CloudFormation > Create stack

![](../deployment/img/start.png)

* Click "Upload a template to Amazon S3" and select `t4.yaml`, provided to you by Quilt
* Click Next
* Fill in Stack name and Parameters

![](../deployment/img/params.png)

> Carefully note parameter descriptions to avoid stack failure

* Click Next
* You can safely skip the Options screen (below) by clicking Next

![](../deployment/img/skip.png)

* Acknowledge that CloudFormation may create IAM roles

![](../deployment/img/finish.png)

* Click Create (typically takes 30 minutes to complete)

* You should see `CREATE_COMPLETE` as the Status for your CloudFormation stack. Select the stack and open the Outputs tab. The Value of `CloudFrontDomain` is your CloudFront origin. Depending on your S3 bucket's [CORS policy](#pre-requisites) your web catalog is available at the CloudFront and/or the `CNAME` set by you in the following step.

![](../deployment/img/outputs.png)

* If desired, set a `CNAME` record with your DNS service that points to your CloudFrontDomain. The `CNAME` must also be present in your [CORS policy](#pre-requisites). Now users can access the T4 catalog at your custom
`CNAME`.
