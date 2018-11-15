import copy
import hashlib
import io
import json
import pathlib
from pathlib import Path
import os
import re

import time

from urllib.parse import quote, urlparse

import jsonlines
from six import string_types, binary_type

from .data_transfer import copy_file, deserialize_obj, get_bytes, put_bytes, TargetType

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

def _to_singleton(physical_keys):
    """
    Ensure that there is a single physical key, throw otherwise.
    Temporary utility method to avoid repeated, identical checks.

    Args:
        pkeys (list): list of physical keys
    Returns:
        A physical key

    Throws:
        NotImplementedError

    TODO:
        support multiple physical keys
    """
    if len(physical_keys) > 1:
        raise NotImplementedError("Multiple physical keys not supported")

    return physical_keys[0]

def get_package_registry(path=None):
    """ Returns the package registry root for a given path """
    if path is None:
        path = BASE_PATH.as_uri()
    return path.rstrip('/') + '/.quilt'


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
        self.physical_keys = [fix_url(x) for x in physical_keys]
        self.size = size
        self.hash = hash_obj
        self.meta = meta

    def __eq__(self, other):
        return (
            # Don't check physical keys.
            self.size == other.size
            and self.hash == other.hash
            and self.meta == other.meta
        )

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

    @classmethod
    def from_local_path(cls, path):
        return cls([], None, None, {})._set_path(path)

    def _clone(self):
        """
        Returns clone of this PackageEntry.
        """
        return self.__class__(copy.deepcopy(self.physical_keys), self.size, \
                              copy.deepcopy(self.hash), copy.deepcopy(self.meta))

    def set_user_meta(self, meta):
        """
        Sets the user_meta for this PackageEntry.
        """
        self.meta['user_meta'] = meta

    def get_user_meta(self):
        """
        Returns the user metadata from this PackageEntry.
        """
        return self.meta.get('user_meta')

    def get_meta(self):
        """
        Returns the metadata from this PackageEntry.
        """
        return self.meta

    def _verify_hash(self, read_bytes):
        """
        Verifies hash of bytes
        """
        if self.hash.get('type') != 'SHA256':
            raise NotImplementedError
        digest = hashlib.sha256(read_bytes).hexdigest()
        if digest != self.hash.get('value'):
            raise QuiltException("Hash validation failed")

    def _set_path(self, path, meta=None):
        """
        Sets the path for this PackageEntry.
        """
        with open(path, 'rb') as file_to_hash:
            hash_obj = {
                'type': 'SHA256',
                'value': hash_file(file_to_hash)
            }

        self.size = os.path.getsize(path)
        self.physical_keys = [pathlib.Path(path).resolve().as_uri()]
        self.hash = hash_obj
        if meta is not None:
            self.set_user_meta(meta)
        return self

    def set(self, path=None, meta=None):
        """
        Returns self with the physical key set to path.

        Args:
            logical_key(string): logical key to update
            path(string): new path to place at logical_key in the package
                Currently only supports a path on local disk
            meta(dict): metadata dict to attach to entry. If meta is provided, set just
                updates the meta attached to logical_key without changing anything
                else in the entry

        Returns:
            self
        """
        if path is not None:
            self._set_path(path, meta)
        elif meta is not None:
            self.set_user_meta(meta)
        else:
            raise PackageException('Must specify either path or meta')

    def get(self):
        """
        Returns the physical key of this PackageEntry.
        """
        return _to_singleton(self.physical_keys)

    def deserialize(self):
        """
        Returns the object this entry corresponds to.

        Returns:
            The deserialized object from the logical_key

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

        physical_key = _to_singleton(self.physical_keys)
        data, _ = get_bytes(physical_key)
        self._verify_hash(data)

        return deserialize_obj(data, target)

    def fetch(self, dest):
        """
        Gets objects from entry and saves them to dest.

        Args:
            dest: where to put the files

        Returns:
            None
        """
        physical_key = _to_singleton(self.physical_keys)
        dest = fix_url(dest)
        copy_file(physical_key, dest, self.meta)

    def __call__(self):
        """
        Shorthand for self.deserialize()
        """
        return self.deserialize()


class Package(object):
    """ In-memory representation of a package """

    def __init__(self, children=None, meta=None):
        self._children = children or {}
        self._meta = meta or {'version': 'v0'}


    @classmethod
    def validate_package_name(cls, name):
        """ Verify that a package name is two alphanumerics strings separated by a slash."""
        if not re.match(PACKAGE_NAME_FORMAT, name):
            raise QuiltException("Invalid package name, must contain exactly one /.")

    @classmethod
    def install(cls, name, registry, pkg_hash=None, dest=None, dest_registry=None):
        """
        Installs a named package to the local registry and downloads its files.

        Args:
            name(str): Name of package to install.
            registry(str): Registry where package is located.
            pkg_hash(str): Hash of package to install. Defaults to latest.
            dest(str): Local path to download files to.
            dest_registry(str): Registry to install package to. Defaults to local registry.

        Returns:
            A new Package that points to files on your local machine.
        """
        if dest_registry is None:
            dest_registry = BASE_PATH

        pkg = cls.browse(name=name, registry=registry, pkg_hash=pkg_hash)
        if dest:
            return pkg.push(name=name, dest=dest, dest_registry=dest_registry)
        else:
            raise NotImplementedError

    @classmethod
    def browse(cls, name=None, registry=None, pkg_hash=None):
        """
        Load a package into memory from a registry without making a local copy of
        the manifest.

        Args:
            name(string): name of package to load
            registry(string): location of registry to load package from
            pkg_hash(string): top hash of package version to load
        """
        registry_prefix = get_package_registry(fix_url(registry) if registry else None)

        if pkg_hash is not None:
            # If hash is specified, name doesn't matter.
            pkg_path = '{}/packages/{}'.format(registry_prefix, pkg_hash)
            return cls._from_path(pkg_path)
        else:
            cls.validate_package_name(name)

        pkg_path = '{}/named_packages/{}/latest'.format(registry_prefix, quote(name))
        latest_bytes, _ = get_bytes(pkg_path)
        latest_hash = latest_bytes.decode('utf-8')

        latest_hash = latest_hash.strip()
        latest_path = '{}/packages/{}'.format(registry_prefix, quote(latest_hash))
        return cls._from_path(latest_path)


    @classmethod
    def _from_path(cls, uri):
        """ Takes a URI and returns a package loaded from that URI """
        src_url = urlparse(uri)
        if src_url.scheme == 'file':
            with open(parse_file_url(src_url)) as open_file:
                pkg = cls.load(open_file)
        elif src_url.scheme == 's3':
            body, _ = get_bytes(uri)
            pkg = cls.load(io.BytesIO(body))
        else:
            raise NotImplementedError
        return pkg

    @classmethod
    def _split_key(cls, logical_key):
        if isinstance(logical_key, string_types):
            path = logical_key.split('/')
        elif isinstance(logical_key, (tuple, list)):
            path = logical_key
        else:
            raise TypeError('Invalid logical_key: %r' % logical_key)
        return path

    def __contains__(self, logical_key):
        """
        Checks whether the package contains a specified logical_key.

        Returns:
            True or False
        """
        try:
            self[logical_key]
            return True
        except KeyError:
            return False

    def __getitem__(self, logical_key):
        """
        Filters the package based on prefix, and returns either a new Package
            or a PackageEntry.

        Args:
            prefix(str): prefix to filter on

        Returns:
            PackageEntry if prefix matches a logical_key exactly
            otherwise Package
        """
        pkg = self
        for key in self._split_key(logical_key):
            pkg = pkg._children[key]
        return pkg

    def fetch(self, dest):
        """
        Copy all descendants to dest. Descendants are written under their logical
        names _relative_ to self. So if p[a] has two children, p[a][b] and p[a][c],
        then p[a].fetch("mydir") will produce the following:
            mydir/
                b
                c

        Args:
            dest: where to put the files (locally)

        Returns:
            None
        """
        # TODO: do this with improved parallelism? connections etc. could be reused
        nice_dest = fix_url(dest).rstrip('/')
        for logical_key, entry in self._walk():
            entry.fetch('{}/{}'.format(nice_dest, quote(logical_key)))

    def keys(self):
        """
        Returns logical keys in the package.
        """
        return self._children.keys()

    def __iter__(self):
        return iter(self._children)

    def __len__(self):
        return len(self._children)

    def _walk(self, prefix=''):
        for name, child in sorted(self._children.items()):
            if isinstance(child, PackageEntry):
                yield prefix + name, child
            else:
                yield from child._walk(prefix + name + '/')

    @classmethod
    def load(cls, readable_file):
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
        reader = jsonlines.Reader(readable_file)
        meta = reader.read()
        # Pop the top hash -- it should only be calculated dynamically
        meta.pop('top_hash', None)
        pkg = cls({}, meta)
        for obj in reader:
            path = cls._split_key(obj.pop('logical_key'))
            subpkg = pkg._ensure_subpackage(path[:-1])
            key = path[-1]
            if key in subpkg._children:
                raise PackageException("Duplicate logical key while loading package")
            subpkg._children[key] = PackageEntry(
                obj['physical_keys'],
                obj['size'],
                obj['hash'],
                obj['meta']
            )

        return pkg

    def set_dir(self, lkey, path):
        """
        Adds all files from path to the package.

        Recursively enumerates every file in path, and adds them to
            the package according to their relative location to path.

        Args:
            lkey(string): prefix to add to every logical key,
                use '/' for the root of the package.
            path(string): path to scan for files to add to package.

        Returns:
            self

        Raises:
            when path doesn't exist
        """
        lkey = lkey.strip("/") + "/"

        if lkey == '/':
            # Prevent created logical keys from starting with '/'
            lkey = ''

        # TODO: deserialization metadata
        url = urlparse(fix_url(path).strip('/'))
        if url.scheme == 'file':
            src_path = pathlib.Path(parse_file_url(url))
            if not src_path.is_dir():
                raise PackageException("The specified directory doesn't exist")
            files = src_path.rglob('*')
            for f in files:
                if not f.is_file():
                    continue
                entry = PackageEntry.from_local_path(f)
                logical_key = lkey + f.relative_to(src_path).as_posix()
                # TODO: Warn if overwritting a logical key?
                self.set(logical_key, entry)
        else:
            raise NotImplementedError

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
        return self[logical_key].get()

    def get_meta(self, logical_key):
        """
        Returns metadata for specified logical key.
        """
        return self[logical_key].meta

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
        registry_prefix = get_package_registry(fix_url(registry) if registry else None)

        hash_string = self.top_hash()
        manifest = io.BytesIO()
        self.dump(manifest)
        put_bytes(
            manifest.getvalue(),
            registry_prefix + '/packages/' + hash_string
        )

        if name:
            # Sanitize name.
            self.validate_package_name(name)

            named_path = registry_prefix + '/named_packages/' + quote(name) + '/'
            # todo: use a float to string formater instead of double casting
            hash_bytes = self.top_hash().encode('utf-8')
            timestamp_path = named_path + str(int(time.time()))
            latest_path = named_path + "latest"
            put_bytes(hash_bytes, timestamp_path)
            put_bytes(hash_bytes, latest_path)

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
        top_level_meta = self._meta
        top_level_meta['top_hash'] = {
            'alg': 'v0',
            'value': self.top_hash()
        }
        writer.write(top_level_meta)
        for logical_key, entry in self._walk():
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
        prefix = "" if not prefix else prefix.strip("/") + "/"
        for logical_key, entry in new_keys_dict.items():
            self.set(prefix + logical_key, entry, meta)
        return self

    def set(self, logical_key, entry, meta=None):
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
        if isinstance(entry, (string_types, binary_type, getattr(os, 'PathLike', str))):
            entry = PackageEntry.from_local_path(entry)
        elif isinstance(entry, PackageEntry):
            entry = entry._clone()
        else:
            raise NotImplementedError("Needs to be of type str")

        if meta is not None:
            entry.meta = meta

        path = self._split_key(logical_key)

        pkg = self._ensure_subpackage(path[:-1])
        pkg._children[path[-1]] = entry

        return self

    def _ensure_subpackage(self, path):
        pkg = self
        for key in path:
            pkg = pkg._children.setdefault(key, Package())
        return pkg

    def delete(self, logical_key):
        """
        Returns the package with logical_key removed.

        Returns:
            self

        Raises:
            KeyError: when logical_key is not present to be deleted
        """
        path = self._split_key(logical_key)
        pkg = self[path[:-1]]
        del pkg._children[path[-1]]
        return self

    def top_hash(self):
        """
        Returns the top hash of the package.

        Note that physical keys are not hashed because the package has
            the same semantics regardless of where the bytes come from.

        Returns:
            A string that represents the top hash of the package
        """
        top_hash = hashlib.sha256()
        hashable_meta = copy.deepcopy(self._meta)
        hashable_meta.pop('top_hash', None)
        print('%r' % hashable_meta)
        top_meta = json.dumps(hashable_meta, sort_keys=True, separators=(',', ':'))
        top_hash.update(top_meta.encode('utf-8'))
        for logical_key, entry in self._walk():
            entry_dict = entry.as_dict()
            entry_dict['logical_key'] = logical_key
            entry_dict.pop('physical_keys', None)
            entry_dict_str = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
            top_hash.update(entry_dict_str.encode('utf-8'))

        return top_hash.hexdigest()

    def push(self, name, dest, registry=None):
        """
        Copies objects to path, then creates a new package that points to those objects.
        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.
        Args:
            name: name for package in registry
            dest: where to copy the objects in the package
            registry: registry where to create the new package
        Returns:
            A new package that points to the copied objects
        """
        self.validate_package_name(name)

        if registry is None:
            registry = dest

        dest_url = fix_url(dest).rstrip('/') + '/' + quote(name)
        if dest_url.startswith('file://') or dest_url.startswith('s3://'):
            pkg = self._materialize(dest_url)
            pkg.build(name, registry=registry)
            return pkg
        else:
            raise NotImplementedError

    def _materialize(self, dest_url):
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
        pkg = self.__class__({}, self._meta)
        # Since all that is modified is physical keys, pkg will have the same top hash
        for logical_key, entry in self._walk():
            # Copy the datafiles in the package.
            physical_key = _to_singleton(entry.physical_keys)
            new_physical_key = dest_url + "/" + quote(logical_key)
            copy_file(physical_key, new_physical_key, entry.meta)

            # Create a new package entry pointing to the new remote key.
            new_entry = entry._clone()
            new_entry.physical_keys = [new_physical_key]
            pkg.set(logical_key, new_entry)
        return pkg

    def diff(self, other_pkg):
        """
        Returns three lists -- added, modified, deleted.

        Added: present in other_pkg but not in self.
        Modified: present in both, but different.
        Deleted: present in self, but not other_pkg.

        Args:
            other_pkg: Package to diff 

        Returns:
            added, modified, deleted (all lists of logical keys)
        """
        deleted = []
        modified = []
        other_entries = dict(other_pkg._walk())
        for lk, entry in self._walk():
            other_entry = other_entries.pop(lk, None)
            if other_entry is None:
                deleted.append(lk)
            elif entry != other_entry:
                modified.append(lk)

        added = list(sorted(other_entries))
        
        return added, modified, deleted
