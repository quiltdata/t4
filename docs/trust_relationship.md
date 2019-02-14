# Setting Up a Trust Relationship

First, create your T4 stack.
Go to your stack in CloudFormation.
Go to its Resources, then find RegistryUser. Click the resource named RegistryUser.
Copy the ARN of the user. Example: arn:aws:iam::730278974607:user/t4-staging-RegistryUser-1CQZVBO2OZO87

If the role you want to use doesn't exist yet, create it now.

In the IAM console, navigate to Roles, and select the role you want to use.

Go to the "Trust Relationships" tab for the role, and select "Edit Trust Relationship".

It should look like this. The contents of the statement may be different.

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Add an object to the beginning of the Statement array, with the following contents:

```
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "$YOUR_REGISTRY_USER_ARN"
      },
      "Action": "sts:AssumeRole"
    },
```

Note the comma after the object. Your trust relationship should now look something like this:
  
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "$YOUR_REGISTRY_USER_ARN"
      },
      "Action": "sts:AssumeRole"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

You are now ready to set up a Quilt Role with this role.
