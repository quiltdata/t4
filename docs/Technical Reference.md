This page provides a technical reference on certain advanced configuration options in T4.

## Deploying the T4 Catalog on AWS

The following instructions use CloudFormation to deploy T4 services to your private AWS account.

1. Ensure you have sufficient permissions to proceed. The `AdministratorAccess` policy is sufficient.
2. If you are going to use Quilt T4 with an existing bucket, it is recommended that you first back up your bucket.
3. If you are going to use Quilt T4 with an existing bucket, make sure that your target bucket has [object versioning enabled](https://docs.aws.amazon.com/AmazonS3/latest/user-guide/enable-versioning.html), as well as the following [CORS policy](https://docs.aws.amazon.com/AmazonS3/latest/dev/cors.html#how-do-i-enable-cors):

    ```xml
    <?xml version="1.0" encoding="UTF-8"?>
    <CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
    <CORSRule>
        <AllowedOrigin>$YOURCOMPANYDOMAIN.COM</AllowedOrigin>
        <AllowedMethod>GET</AllowedMethod>
        <AllowedMethod>HEAD</AllowedMethod>
        <AllowedMethod>PUT</AllowedMethod>
        <AllowedMethod>POST</AllowedMethod>
        <AllowedHeader>*</AllowedHeader>
        <MaxAgeSeconds>3000</MaxAgeSeconds>
    </CORSRule>
    </CORSConfiguration>
    ```

    > Note: bucket CORS does not grant permissions of any kind.
    > `AllowedMethod` actions are only available to IAM users or roles with sufficient permissions.

    Note the `AllowedOrigin` field. This should be parameterized with the domain you will host your catalog from. For example, `https://yourcompany.com`.

    If you are going to use Quilt T4 with a new bucket, create the bucket now, and set these policies as part of the flow for bucket creation.

4. Create, or ensure you have already created, an [AWS TLS Certificate](https://aws.amazon.com/certificate-manager/) which maps to the public domain name you want your catalog to use. For example, if you want your catalog to be publicly accessible from `t4.foo.com`, you will need to have a certificate for `t4.foo.com` or `*.foo.com` registered in your account.

   An AWS certificate is an Amazon-issued HTTPS certificate, created via the [AWS Certificate Manager service](https://aws.amazon.com/certificate-manager/), and it's a necessity because it enables HTTPS access to your catalog. If you have not created one, [step through the flow for creating one now](https://docs.aws.amazon.com/acm/latest/userguide/gs-acm-request-public.html). If you already have a certificate for your website, but it's not an AWS-issued certificate, see the instructions on [importing an external certificate into AWS](https://docs.aws.amazon.com/acm/latest/userguide/import-certificate.html).

5. Go to `Services > CloudFormation > Create stack` in your AWS Console.

    ![](./imgs/start.png)

6. Click "Upload a template to Amazon S3" and select the `t4-deployment.yaml` file provided to you by Quilt. Click Next.

7. You should now be at the stack parameters screen. This is where you will fill out of all of the configurable details of your Quilt T4 instance. These are, in order:

    * **Stack name**&mdash;CloudFormation will deploy your T4 catalog instance and all of its associated services as a "stack" with this name. This name is currently only used for administering your resources; it will not be seen by end users.
    * **AdminEmail**, **AdminPassword**, **AdminUsername**&mdash;This is the account login for the initial catalog administrator account. Only admins can configure catalog permissions. The initial admin account can promote other accounts to admin.
    * **BucketDescription**, **BucketIcon**, **BucketTitle**&mdash;A bucket title and description, and a URL pointing to a (preferably square) image (in any reasonable image format) that will be used as the bucket logo. These fields are exposed to users in the catalog selection dropdown menu:
    ![](./imgs/buckets_dropdown.png)

      > These values cannot be updated after-the-fact using AWS CloudFormation. Instead, see the instructions in the section "Federations and bucket config".

    * **CertificateArn**&mdash;The [ARN](https://docs.aws.amazon.com/general/latest/gr/aws-arns-and-namespaces.html) associated with the HTTP certificate you will use for HTTPS access to the catalog. See step 3 for instructions on getting one.
    * **ConfigBucketName**&mdash;Name of a new S3 bucket that will be created automatically by the stack. This bucket will be used to store certain configuration files associated with your catalog instance. The bucket name must be globally unique, e.g. it cannot point to a bucket that already exists (even if that bucket is in your account).

      We recommend a bucket name ending in `-config`, to make it more obvious that this bucket is configuration-only.
    * **DBPassword**&mdash;The auth database password. This doesn't need to be very secure because it will not be publicly accessible. You should only need to access the auth database directly in unusual circumstances.
    * **DefaultSender**, **MixPanelToken**, **ProductCode**&mdash;These are Quilt-set fields with autogenerated values that can be safely ignored.
    * **QuiltBucketName**&mdash;Name of the S3 bucket that this catalog instance will be based out of. This should be the same S3 bucket that you configured for access authorization in step 2.
    * **QuiltWebHost**&mdash;The URL that your catalog will be served out of. Must pattern match the AWS certificate you provide to the `CertificateARN` field. For example, an AWS certificate for `*.foo.com` allows for `t4.foo.com` or `catalog.foo.com` as your `QuiltWebHost`, but not `t4.notfoo.com`.
    * **RegistryHost**&mdash;The URL that the T4 auth service will be served out of. As with `QuiltWebHost`, this field must pattern match the AWS certificate you provide in `CertificateARN`. It may not be the same value as `QuiltWebHost`.

      We recommend appending `-registry` to namespace you set in `QuiltWebHost`. For example, `catalog.foo.com` and `catalog-registry.foo.com`.
    * **SecretKey**&mdash;Used for session authorization. Provide a random value to this field (e.g. by running `uuidgen | sha256sum` in the command line).
    * **SentryDSN** &mdash; Set this field to a single dash: `-`.
    * **SmtpHost**, **SmtpPassword**, **SmtpUsername**&mdash;Log-in information for an SMTP mail server. These fields are necessary because the T4 catalog will need to send (very occassional) service emails on your behalf.
    * **Users**&mdash;Comma-separated list of ARNs of IAM users and/or IAM roles that will be able to perform searches in the bucket.

      Note that users with search access can see the entire contents of the bucket. Use with care.

8. Click Next.
9. On the Options screen that follows, go to the "Termination Protection" section in "Advanced" and click "Enable".

    ![](./imgs/term_protect.png)

    This protects the stack deployment pipeline from accidental deletion. Click Next.

10. On the confirmation screen, check the box asking you to acknowledge that CloudFormation may create IAM roles, then click Create.

    ![](./imgs/finish.png)

    Click Create.

11. CloudFormation typically takes around 30 minutes to spin up your stack. Once that is done, you should see `CREATE_COMPLETE` as the Status for your CloudFormation stack.

    ![](./imgs/outputs.png)

12. Select the stack and open the Outputs tab. Copy the `CloudFrontDomain` value&mdash;this is your CloudFront origin.

13. Set a `CNAME` record with your DNS service that points to your `CloudFrontDomain`. Double check that this the `CloudFrontDomain` value matches the `AllowedOrigin` value in the CORS policy you set in step 1.

If all went well, your catalog should now be available and accessible.

## Known limitations

Some known limitations of the catalog are:

* Supports only one bucket
* Search is only enabled for *new objects* uploaded through the T4 Python API

## Federations and bucket config

In this section we will discuss how you can configure your catalog instance using _federations_ and _bucket config_.

When you create your T4 stack, you specify a *ConfigBucketName* in your stack parameters. This bucket will be created and populated with two files -- `config.json` and `federation.json`. `config.json` is the main navigator config file, and contains things that are specific to your navigator, like `defaultBucket` and `signInRedirect`. It also includes one or more references to federations, including your `federation.json`. `federation.json` is your default federation. It includes an inline bucket config for your T4 bucket.

A **federation** is just a list of bucket configurations. Your catalog will specify one or more federations from which it sources its bucket configs. Federations are a convenient way to manage collections of buckets that are useful in groups, like all the T4 buckets owned by a specific group or all public T4 buckets pertaining to a certain field. Each bucket configuration in a federation can be either a hyperlink (possibly relative) to a JSON file containing the bucket config, or an object containing the bucket config itself. 

An example:

```json
{
  "buckets": [
    {
      "... inline bucket config ..."
    },
    "link/to/bucket/config.json",
    "..."
  ]
}
```

A **bucket config**, meanwhile, is a JSON object that describes metadata associated with a T4 bucket. It is of the following form:

```json
{
  "name": "name of s3 bucket",
  "title": "friendly title to be displayed in the catalog drop-down",
  "icon": "square icon to be displayed in the catalog drop-down",
  "description": "short description of the bucket to be displayed in the catalog drop-down",
  "searchEndpoint": "url of the search endpoint for your T4 bucket"
}
```

A bucket config can be included inline in a federation, or it can be a standalone JSON file that is linked from a federation.

## Preparing an AWS Role for use with T4

These instructions document how to set up an existing role for use with T4. If the role you want to use doesn't exist yet, create it now.

Go to your T4 stack in CloudFormation. Go to `Resources`, then find `RegistryUser` and click on the linked user.
Copy the `ARN` of that user. This will look something like this: `arn:aws:iam::730278974607:user/t4-staging-RegistryUser-1CQZVBO2OZO87`.

Go to the IAM console and navigate to `Roles`. Select the role you want to use. Go to the `Trust Relationships` tab for the role, and select `Edit Trust Relationship`. The statement might look something like this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    "... one or more statements"
  ]
}
```

Add an object to the beginning of the Statement array with the following contents:

```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "$YOUR_REGISTRY_USER_ARN"
  },
  "Action": "sts:AssumeRole"
},
```

Note the comma after the object. Your trust relationship should now look something like this:

```json
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
    "... whatever was here before"
  ]
}
```

You can now configure a Quilt Role with this role (using the Catalog's admin panel, or `t4.admin.create_role`).

## Configuring search file types

This section describes how to configure what types of files are indexed and searchable in the catalog.

To modify which file types are searchable, populate a `.quilt/config.json` file in your S3 bucket. Note that this file does not exist by default. The contents of the file shoud be something like this:

```json
{
    "ipynb": true,
    "json": true,
    "md": true
}
```

To change which file types are searchable, push a new JSON fragment like this one to the `.quilt/config.json` path in the bucket.

> There are currently some important limitations with search:
>
> * Queries containing the tilde (~), forward slash (/), back slash, and angle bracket ({, }, (, ), [, ]) must be quoted. For example search for `'~foo'`, not `~foo`.
> * The search index will only pick up objects written to S3 _after_ T4 was enabled on that bucket.
> * Files over 10 MB in size may cause search to fail.

## Making your search endpoint publicly accessible

This section describes how to make your search endpoint available to anyone with valid AWS credentials.

Go to your AWS Console. Under the `Services` dropdown at the top of the screen, choose `Elasticsearch Service`. Select the domain corresponding to your T4 stack.

Note the value of the `Domain ARN` for your search domain.

In the row of buttons at the top of the pane, select `Modify Access Policy`. Add two statements to the Statement array:

```json
{
  "Effect": "Allow",
    "Principal": {
      "AWS": "*"
    },
    "Action": "es:ESHttpGet",
    "Resource": "$YOUR_SEARCH_DOMAIN_ARN/*"
},
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "*"
  },
  "Action": "es:ESHttpPost",
  "Resource": "$YOUR_SEARCH_DOMAIN_ARN/drive/_doc/_search*"
}
```

Select `Submit` and your search domain should now be open to the public.
