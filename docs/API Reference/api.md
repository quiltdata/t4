
# t4
T4 API

## config(\*autoconfig\_url, \*\*config\_values)  {#config}
Set or read the T4 configuration.

To retrieve the current config, call directly, without arguments:

```python
    >>> import t4
    >>> t4.config()
```

To trigger autoconfiguration, call with just the navigator URL:

```python
    >>> t4.config('https://example.com')
```

To set config values, call with one or more key=value pairs:

```python
    >>> t4.config(navigator_url='http://example.com',
    ...           elastic_search_url='http://example.com/queries')
```

When setting config values, unrecognized values are rejected.  Acceptable
config values can be found in `t4.util.CONFIG_TEMPLATE`.

__Arguments__

* __autoconfig_url__:  A (single) URL indicating a location to configure from
* __**config_values__:  `key=value` pairs to set in the config

__Returns__

`T4Config`: (an ordered Mapping)


## copy(src, dest)  {#copy}

Copies ``src`` object from T4 to ``dest``.

Either of ``src`` and ``dest`` may be S3 paths (starting with ``s3://``)
or local file paths (starting with ``file:///``).

__Arguments__

* __src (str)__:  a path to retrieve
* __dest (str)__:  a path to write to


## delete\_package(name, registry=None)  {#delete\_package}

Delete a package. Deletes only the manifest entries and not the underlying files.

__Arguments__

* __name (str)__:  Name of the package
* __registry (str)__:  The registry the package will be removed from


## get(src)  {#get}
Retrieves src object from T4 and loads it into memory.

An optional ``version`` may be specified.

__Arguments__

* __src (str)__:  A URI specifying the object to retrieve

__Returns__

`tuple`: ``(data, metadata)``.  Does not work on all objects.


## list\_packages(registry=None)  {#list\_packages}
Lists Packages in the registry.

Returns a list of all named packages in a registry.
If the registry is None, default to the local registry.

__Arguments__

* __registry(string)__:  location of registry to load package from.

__Returns__

A list of strings containing the names of the packages


## put(obj, dest, meta=None)  {#put}
Write an in-memory object to the specified T4 ``dest``.

Note:
    Does not work with all objects -- object must be serializable.

You may pass a dict to ``meta`` to store it with ``obj`` at ``dest``.

__Arguments__

* __obj__:  a serializable object
* __dest (str)__:  A URI
* __meta (dict)__:  Optional. metadata dict to store with ``obj`` at ``dest``


## search(query)  {#search}

Searches your bucket. query can contain plaintext, and can also contain clauses
like $key:"$value" that search for exact matches on specific keys.

Returns either the request object (in case of an error) or a list of objects with the following keys:
    key: key of the object
    version_id: version_id of object version
    operation: Create or Delete
    meta: metadata attached to object
    size: size of object in bytes
    text: indexed text of object
    source: source document for object (what is actually stored in ElasticSeach)
    time: timestamp for operation

