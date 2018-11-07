import copy
import hashlib
import io
import json
import pathlib
from pathlib import Path
import os
import re

import tempfile
import time

from urllib.parse import quote, urlparse

import jsonlines

from .data_transfer import copy_file, deserialize_obj, download_bytes, TargetType

from .exceptions import PackageException
from .util import QuiltException, BASE_PATH, fix_url, PACKAGE_NAME_FORMAT, parse_file_url, \
    parse_s3_url


def hash_file(readable_file):
    """ Returns SHA256 hash of readable file-like object """
    buf = readable_file.read(4096)
    hasher = hashlib.sha256()
    while buf:
        hasher.update(buf)
        buf = readable_file.read(4096)

    return hasher.hexdigest()

def read_physical_key(physical_key):
    # TODO: Stream the data.
    url = urlparse(physical_key)
    if url.scheme == 'file':
        with open(parse_file_url(url), 'rb') as fd:
            return fd.read()
    elif url.scheme == 's3':
        bucket, path, version_id = parse_s3_url(url)
        return download_bytes(bucket + '/' + path, version_id)[0]
    else:
        raise NotImplementedError


def get_package_registry(path=''):
    """ Returns the package registry root for a given path """
    if path.startswith('s3://'):
        bucket = path[5:].partition('/')[0]
        return "s3://{}/.quilt".format(bucket)
    # Default to the local registry.
    return get_local_package_registry().as_uri()

def get_local_package_registry():
    """ Returns a local package registry Path. """
    Path(BASE_PATH, "packages").mkdir(parents=True, exist_ok=True)
    Path(BASE_PATH, "named_packages").mkdir(parents=True, exist_ok=True)
    return BASE_PATH

class PackageEntry(object):
    """
    Represents an entry at a logical key inside a package.
    """
    __slots__ = ['physical_keys', 'size', 'hash', 'meta']
    def __init__(self, physical_keys, size, hash_obj, meta):
        """
        Creates an entry.

        Args:
            physical_keys is a nonempty list of URIs (either s3:// or file://)
            size(number): size of object in bytes
            hash({'type': string, 'value': string}): hash object
                for example: {'type': 'SHA256', 'value': 'bb08a...'}
            meta(dict): metadata dictionary

        Returns:
            a PackageEntry
        """
        assert physical_keys
        self.physical_keys = [fix_url(x) for x in physical_keys]
        self.size = size
        self.hash = hash_obj
        self.meta = meta

    def as_dict(self):
        """
        Returns dict representation of entry.
        """
        ret = {
            'physical_keys': self.physical_keys,
            'size': self.size,
            'hash': self.hash,
            'meta': self.meta
        }
        return copy.deepcopy(ret)

    @staticmethod
    def from_local_path(path):
        with open(path, 'rb') as file_to_hash:
            hash_obj = {
                'type': 'SHA256',
                'value': hash_file(file_to_hash)
            }

        size = os.path.getsize(path)
        physical_keys = [pathlib.Path(path).resolve().as_uri()]
        return PackageEntry(physical_keys, size, hash_obj, {})

    def _clone(self):
        """
        Returns clone of this package.
        """
        return PackageEntry(copy.deepcopy(self.physical_keys), self.size, \
                            copy.deepcopy(self.hash), copy.deepcopy(self.meta))

    def set_user_meta(self, meta):
        """
        Sets the user_meta for this PackageEntry.
        """
        self.meta['user_meta'] = meta

    def user_meta(self):
        """
        Returns the user metadata from this PackageEntry.
        """
        return self.meta.get('user_meta')

    def _verify_hash(self, read_bytes):
        """
        Verifies hash of bytes
        """
        if self.hash.get('type') != 'SHA256':
            raise NotImplementedError
        digest = hashlib.sha256(read_bytes).hexdigest()
        if digest != self.hash.get('value'):
            raise QuiltException("Hash validation failed")

    def get(self):
        """
        Returns the physical key of this PackageEntry.
        """
        if len(self.physical_keys) > 1:
            raise NotImplementedError
        return self.physical_keys[0]

    def deserialize(self):
        return self._get()[0]

    def _get(self):
        """
        Returns a tuple of the object this entry corresponds to and its metadata.

        Returns:
            A tuple containing the deserialized object from the logical_key and its metadata

        Raises:
            physical key failure
            hash verification fail
            when deserialization metadata is not present
        """
        target_str = self.meta.get('target')
        if target_str is None:
            raise QuiltException("No serialization metadata")

        try:
            target = TargetType(target_str)
        except ValueError:
            raise QuiltException("Unknown serialization target: %r" % target_str)

        physical_keys = self.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys

        data = read_physical_key(physical_key)

        self._verify_hash(data)

        return deserialize_obj(data, target), self.meta.get('user_meta')

    def __call__(self):
        """
        Shorthand for self.deserialize()
        """
        return self.deserialize()


class Package(object):
    """ In-memory representation of a package """

    @staticmethod
    def validate_package_name(name):
        """ Verify that a package name is two alphanumerics strings separated by a slash."""
        if not re.match(PACKAGE_NAME_FORMAT, name):
            raise QuiltException("Invalid package name, must contain exactly one /.")

    @staticmethod
    def install(name, dest=None, registry=None, pkg_hash=None):
        """
        Installs a named package to the local registry and downloads its files.

        Args:
            name(str): Name of package to install.
            dest(str): Local path to download files to.
                Defaults to $local_registry/files/{sha256 of file}
            registry(str): Registry to install package to. Defaults to local registry.
            pkg_hash(str): Hash of package to install. Defaults to latest.

        Returns:
            A new Package that points to files on your local machine.
        """
        pkg = Package(name=name, pkg_hash=pkg_hash, registry=registry or '')
        if dest:
            return pkg.push(path=dest, name=name)
        else:
            raise NotImplementedError

    def __init__(self, name=None, pkg_hash=None, registry=''):
        """
        Create a Package from scratch, or load one from a registry.

        Args:
            name(string): name of package to load
            pkg_hash(string): top hash of package version to load
            registry(string): location of registry to load package from
        """
        if name is None and pkg_hash is None:
            self._data = {}
            self._meta = {'version': 'v0'}
            return
        elif name:
            self.validate_package_name(name)

        registry = get_package_registry(fix_url(registry))

        if pkg_hash is not None:
            # If hash is specified, name doesn't matter.
            pkg_path = '{}/packages/{}'.format(registry, pkg_hash)
            pkg = self._from_path(pkg_path)
            # Can't assign to self, so must mutate.
            self._set_state(pkg._data, pkg._meta)
            return

        pkg_path = '{}/named_packages/{}/'.format(registry, quote(name))
        latest = urlparse(pkg_path + 'latest')
        if latest.scheme == 'file':
            latest_path = parse_file_url(latest)
            with open(latest_path) as latest_file:
                latest_hash = latest_file.read()
        elif latest.scheme == 's3':
            bucket, path, vid = parse_s3_url(latest)
            latest_bytes, _ = download_bytes(bucket + '/' + path, version=vid)
            latest_hash = latest_bytes.decode('utf-8')
        else:
            raise NotImplementedError

        latest_hash = latest_hash.strip()
        latest_path = '{}/packages/{}'.format(registry, quote(latest_hash))
        pkg = self._from_path(latest_path)
        # Can't assign to self, so must mutate.
        self._set_state(pkg._data, pkg._meta)


    @staticmethod
    def _from_path(uri):
        """ Takes a URI and returns a package loaded from that URI """
        src_url = urlparse(uri)
        if src_url.scheme == 'file':
            with open(parse_file_url(src_url)) as open_file:
                pkg = Package.load(open_file)
        elif src_url.scheme == 's3':
            bucket, path, vid = parse_s3_url(urlparse(src_url.geturl()))
            body, _ = download_bytes(bucket + '/' + path, version=vid)
            pkg = Package.load(io.BytesIO(body))
        else:
            raise NotImplementedError
        return pkg


    def _set_state(self, data, meta):
        self._data = data
        self._meta = meta
        return self

    def _clone(self):
        """
        Returns clone of this package.
        """
        return Package()._set_state(copy.deepcopy(self._data), copy.deepcopy(self._meta))

    def __contains__(self, logical_key):
        """
        Checks whether the package contains a specified logical_key.

        Returns:
            True or False
        """
        return logical_key in self._data

    def __getitem__(self, prefix):
        """
        Filters the package based on prefix, and returns either a new Package
            or a PackageEntry.

        Args:
            prefix(str): prefix to filter on

        Returns:
            PackageEntry if prefix matches a logical_key exactly
            otherwise Package
        """
        if prefix in self._data:
            return self._data[prefix]
        result = Package()
        slash_prefix = prefix.rstrip('/') + '/' # ensure it ends with exactly one /
        for key, entry in self._data.items():
            if key.startswith(slash_prefix):
                new_key = key[len(slash_prefix):]
                result.set(new_key, entry)
        return result

    def keys(self):
        """
        Returns list of logical_keys in the package.
        """
        return list(self._data.keys())

    @staticmethod
    def load(readable_file):
        """
        Loads a package from a readable file-like object.

        Args:
            readable_file: readable file-like object to deserialize package from

        Returns:
            a new Package object

        Raises:
            file not found
            json decode error
            invalid package exception
        """
        data = {}
        reader = jsonlines.Reader(readable_file)
        meta = reader.read()
        for obj in reader:
            lk = obj.pop('logical_key')
            if lk in data:
                raise PackageException("Duplicate logical key while loading package")
            data[lk] = PackageEntry(
                obj['physical_keys'],
                obj['size'],
                obj['hash'],
                obj['meta']
            )

        return Package()._set_state(data, meta)

    def capture(self, path, prefix=None):
        """
        Adds all files from path to the package.

        Recursively enumerates every file in path, and adds them to
            the package according to their relative location to path.

        Args:
            path(string): path to package

        Returns:
            self

        Raises:
            when path doesn't exist
        """
        prefix = "" if not prefix else quote(prefix).strip("/") + "/"

        # TODO: anything but local paths
        # TODO: deserialization metadata
        src_path = pathlib.Path(path)
        files = src_path.rglob('*')
        for f in files:
            if not f.is_file():
                continue
            entry = PackageEntry.from_local_path(f)
            logical_key = prefix + f.relative_to(src_path).as_posix()
            # TODO: Warn if overwritting a logical key?
            self.set(logical_key, entry)

        # Must unset old top hash when modifying package.
        self._unset_tophash()
        return self

    def get(self, logical_key):
        """
        Gets object from local_key and returns it as an in-memory object.

        Args:
            logical_key(string): logical key of the object to get

        Returns:
            A tuple containing the deserialized object from the logical_key and its metadata

        Raises:
            KeyError: when logical_key is not present in the package
            physical key failure
            hash verification fail
            when deserialization metadata is not present
        """
        entry = self._data[logical_key]

        return entry.get()

    def copy(self, logical_key, dest):
        """
        Gets objects from logical_key inside the package and saves them to dest.

        Args:
            logical_key: logical key inside package to get
            dest: where to put the files

        Returns:
            None

        Raises:
            logical key not found
            physical key failure
            fail to create file
            fail to finish write
        """
        entry = self._data[logical_key]

        physical_keys = entry.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys

        dest = fix_url(dest)

        copy_file(physical_key, dest, entry.meta)

    def get_meta(self, logical_key):
        """
        Returns metadata for specified logical key.
        """
        entry = self._data[logical_key]
        return entry.meta

    def build(self, name=None, registry=None):
        """
        Serializes this package to a registry.

        Args:
            name: optional name for package
            registry: registry to build to
                    defaults to local registry

        Returns:
            the top hash as a string
        """
        if registry is not None:
            registry = get_package_registry(fix_url(registry))
        else:
            registry = get_package_registry()

        hash_string = self.top_hash()
        with tempfile.NamedTemporaryFile() as manifest:
            self.dump(manifest)
            manifest.flush()
            copy_file(
                pathlib.Path(manifest.name).resolve().as_uri(),
                registry.strip('/') + '/' + "packages/" + hash_string,
                {}
            )

        if name:
            # Sanitize name.
            self.validate_package_name(name)
            name = quote(name)

            named_path = registry.strip('/') + '/named_packages/' + quote(name) + '/'
            # todo: use a float to string formater instead of double casting
            with tempfile.NamedTemporaryFile() as hash_file:
                hash_file.write(self.top_hash().encode('utf-8'))
                hash_file.flush()
                hash_uri = pathlib.Path(hash_file.name).resolve().as_uri()
                timestamp_path = named_path + str(int(time.time()))
                latest_path = named_path + "latest"
                copy_file(hash_uri, timestamp_path, {})
                hash_file.seek(0)
                copy_file(hash_uri, latest_path, {})

        return hash_string

    def dump(self, writable_file):
        """
        Serializes this package to a writable file-like object.

        Args:
            writable_file: file-like object to write serialized package.

        Returns:
            None

        Raises:
            fail to create file
            fail to finish write
        """
        self.top_hash() # Assure top hash is calculated.
        writer = jsonlines.Writer(writable_file)
        writer.write(self._meta)
        for logical_key, entry in self._data.items():
            writer.write({'logical_key': logical_key, **entry.as_dict()})

    def update(self, new_keys_dict, meta=None, prefix=None):
        """
        Updates the package with the keys and values in new_keys_dict.

        If a metadata dict is provided, it is attached to and overwrites
        metadata for all entries in new_keys_dict.

        Args:
            new_dict(dict): dict of logical keys to update.
            meta(dict): metadata dict to attach to every input entry.
            prefix(string): a prefix string to prepend to every logical key.

        Returns:
            self

        """
        prefix = "" if not prefix else quote(prefix).strip("/") + "/"
        for logical_key, entry in new_keys_dict.items():
            self.set(prefix + logical_key, entry, meta)
        self._unset_tophash()
        return self

    def set(self, logical_key, entry=None, meta=None):
        """
        Returns self with the object at logical_key set to entry.

        Args:
            logical_key(string): logical key to update
            entry(PackageEntry OR string): new entry to place at logical_key in the package
                if entry is a string, it is treated as a path to local disk and an entry
                is created based on the file at that path on your local disk
            meta(dict): metadata dict to attach to entry. If meta is provided, set just
                updates the meta attached to logical_key without changing anything
                else in the entry

        Returns:
            self
        """
        if entry is None and meta is None:
            raise PackageException('Must specify either entry or meta')

        if entry is None:
            return self._update_meta(logical_key, meta)

        if isinstance(entry, str):
            entry = PackageEntry.from_local_path(entry)
            if meta is not None:
                entry.meta = meta
            self._data[logical_key] = entry
        elif isinstance(entry, PackageEntry):
            if meta is not None:
                raise PackageException("Must specify metadata in the entry")
            self._data[logical_key] = entry
        else:
            raise NotImplementedError

        # Must unset old top hash when modifying package
        self._unset_tophash()
        return self

    def _update_meta(self, logical_key, meta):
        self._data[logical_key].meta = meta
        self._unset_tophash()
        return self

    def delete(self, logical_key):
        """
        Returns the package with logical_key removed.

        Returns:
            self

        Raises:
            KeyError: when logical_key is not present to be deleted
        """
        self._data.pop(logical_key)
        # Must unset old top hash when modifying package
        self._unset_tophash()
        return self

    def _top_hash(self):
        """
        Sets the top_hash in _meta

        Returns:
            None
        """
        top_hash = hashlib.sha256()
        hashable_meta = copy.deepcopy(self._meta)
        hashable_meta.pop('top_hash', None)
        top_meta = json.dumps(hashable_meta, sort_keys=True, separators=(',', ':'))
        top_hash.update(top_meta.encode('utf-8'))
        for logical_key, entry in sorted(list(self._data.items())):
            entry_dict = entry.as_dict()
            entry_dict['logical_key'] = logical_key
            entry_dict.pop('physical_keys', None)
            entry_dict_str = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
            top_hash.update(entry_dict_str.encode('utf-8'))

        self._meta['top_hash'] = {
            'alg': 'v0',
            'value': top_hash.hexdigest()
        }

    def _unset_tophash(self):
        """
        Unsets the top hash
        When a package is created from an existing package, the top hash
            must be deleted so a correct new one can be calculated
            when necessary
        """
        self._meta.pop('top_hash', None)

    def top_hash(self):
        """
        Returns the top hash of the package.

        Note that physical keys are not hashed because the package has
            the same semantics regardless of where the bytes come from.

        Returns:
            A string that represents the top hash of the package
        """
        if 'top_hash' not in self._meta:
            self._top_hash()
        return self._meta['top_hash']['value']

    def push(self, path, name=None):
        """
        Copies objects to path, then creates a new package that points to those objects.
        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.
        Args:
            path: where to copy the objects in the package
            name: name for package in registry
        Returns:
            A new package that points to the copied objects
        """
        dest = fix_url(path).strip('/')
        if name:
            self.validate_package_name(name)
            dest = dest + '/' + quote(name)
        if dest.startswith('file://') or dest.startswith('s3://'):
            pkg = self._materialize(dest)
            pkg.build(name, registry=get_package_registry(dest))
            return pkg
        else:
            raise NotImplementedError

    def _materialize(self, path):
        """
        Copies objects to path, then creates a new package that points to those objects.

        Copies each object in this package to path according to logical key structure,
        and returns a package with physical_keys that point to the new copies.

        Args:
            path: where to copy the objects in the package

        Returns:
            A new package that points to the copied objects

        Raises:
            fail to get bytes
            fail to put bytes
            fail to put package to registry
        """
        pkg = self._clone()
        # Since all that is modified is physical keys, pkg will have the same top hash
        for logical_key, entry in self._data.items():
            # Copy the datafiles in the package.
            new_physical_key = path + "/" + quote(logical_key)

            self.copy(logical_key, new_physical_key)
            # Create a new package pointing to the new remote key.
            new_entry = entry._clone()
            new_entry.physical_keys = [new_physical_key]
            # Treat as a local path
            pkg = pkg.set(logical_key, new_entry)
        return pkg
