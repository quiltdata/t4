# Configuring the Navigator

When you create your T4 stack, you specify a *ConfigBucketName* in your stack parameters. This bucket will be created and populated with two files -- `config.json` and `federation.json`. `config.json` is the main navigator config file, and contains things that are specific to your navigator, like `defaultBucket` and `signInRedirect`. It also includes one or more references to federations, including your `federation.json`. `federation.json` is your default federation. It includes an inline bucket config for your T4 bucket.

# Federations

A Federation is just a list of bucket configurations. Your catalog will specify one or more federations from which it sources its bucket configs. Federations are a convenient way to manage collections of buckets that are useful in groups, like all the T4 buckets owned by a specific group or all public T4 buckets pertaining to a certain field. Each bucket configuration in a federation can be either a hyperlink (possibly relative) to a JSON file containing the bucket config, or an object containing the bucket config itself. 

## Example:

```
{
  'buckets': [
    {
      ... inline bucket config ...
    },
    'link/to/bucket/config.json',
    ...
  ]
}
```

# Bucket Config

A Bucket Config is a JSON object that describes metadata associated with a T4 bucket. It is of the following form:

```
{
  'name': name of s3 bucket,
  'title': friendly title to be displayed in the catalog drop-down,
  'icon': square icon to be displayed in the catalog drop-down,
  'description': short description of the bucket to be displayed in the catalog drop-down,
  'searchEndpoint': url of the search endpoint for your T4 bucket
}
```

A bucket config can be included inline in a federation, or it can be a standalone JSON file that is linked from a federation.
