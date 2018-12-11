from collections import deque
import copy
import hashlib
import io
import json
import pathlib
import os

import time

from urllib.parse import quote, urlparse

import jsonlines
from six import string_types

from .data_transfer import (
    calculate_sha256, copy_file, deserialize_obj,
    get_bytes, get_size_and_meta, list_object_versions, put_bytes,
    TargetType
)
from .exceptions import PackageException
from .util import (
    QuiltException, BASE_PATH, fix_url, parse_file_url, parse_s3_url, validate_package_name
)


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
        self.meta = meta or {}

    def __eq__(self, other):
        return (
            # Don't check physical keys.
            self.size == other.size
            and self.hash == other.hash
            and self.meta == other.meta
        )

    def __repr__(self):
        return f"PackageEntry('{self.physical_keys[0]}')"

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
        if self.hash is None:
            raise QuiltException("Hash missing - need to build the package")
        if self.hash.get('type') != 'SHA256':
            raise NotImplementedError
        digest = hashlib.sha256(read_bytes).hexdigest()
        if digest != self.hash.get('value'):
            raise QuiltException("Hash validation failed")

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
            self.physical_keys = [fix_url(path)]
            self.size = None
            self.hash = None
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

    def __init__(self):
        self._children = {}
        self._meta = {'version': 'v0'}

    def _unlimited_repr(self, level=0, indent='  '):
        """
        String representation without line limit.
        """
        self_repr = ''
        for child_key in sorted(self.keys()):
            if isinstance(self[child_key], Package):
                child_entry = indent*level + child_key + '/\n'
                self_repr += child_entry
                self_repr += self[child_key].__repr__(level+1, indent)
            else: # leaf node
                self_repr += indent*level + child_key + '\n'
        return self_repr

    def __repr__(self, max_lines=20):
        """
        String representation of the Package.
        """
        if not self.keys():
            return "(empty Package)"

        if max_lines is None:
            return self._unlimited_repr()

        if len(self.keys()) > max_lines:
            # If there aren't enough lines to display all top-level children,
            #   display as many as possible with a '...' at the end
            self_repr = ''
            i = 0
            for key in sorted(self.keys()):
                if i >= max_lines - 1:
                    self_repr += '...\n'
                    return self_repr
                if isinstance(self[key], Package):
                    key = key + '/'
                self_repr += key + '\n'
                i += 1
            assert False, "This should never happen"

        def _create_str(results_dict, level=0, indent='  '):
            """
            Creates a string from the results dict
            """
            result = ''
            for key in sorted(results_dict.keys()):
                result += indent*level + key + '\n'
                result += _create_str(results_dict[key], level+1, indent)
            return result

        # candidates is a deque of 
        #     ((logical_key, Package | PackageEntry), [list of parent key])
        candidates = deque(([x, []] for x in self._children.items()))
        results_dict = {}
        results_total = 0
        while len(candidates) and results_total < max_lines:
            [[logical_key, entry], parent_keys] = candidates.popleft()
            if isinstance(entry, Package):
                logical_key = logical_key + '/'
                new_parent_keys = parent_keys.copy()
                new_parent_keys.append(logical_key)
                for child_key in sorted(entry.keys()):
                    candidates.append([[child_key, entry[child_key]], new_parent_keys])

            current_result_level = results_dict
            for key in parent_keys:
                current_result_level = current_result_level[key]
            current_result_level[logical_key] = {}
            results_total += 1

        return _create_str(results_dict)

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
            return pkg.push(name=name, dest=dest, registry=dest_registry)
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
            validate_package_name(name)

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
        """
        Converts a string logical key like 'a/b/c' into a list of ['a', 'b', 'c'].
        Returns the original key if it's already a list or a tuple.
        """
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
        for key_fragment in self._split_key(logical_key):
            pkg = pkg._children[key_fragment]
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
        for logical_key, entry in self.walk():
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

    def walk(self):
        """
        Generator that traverses all entries in the package tree and returns tuples of (key, entry),
        with keys in alphabetical order.
        """
        for name, child in sorted(self._children.items()):
            if isinstance(child, PackageEntry):
                yield name, child
            else:
                for key, value in child.walk():
                    yield name + '/' + key, value

    def _walk_dir_meta(self):
        """
        Generator that traverses all entries in the package tree and returns
            tuples of (key, meta) for each directory with metadata.
        Keys will all end in '/' to indicate that they are directories.
        """
        for key, child in sorted(self._children.items()):
            if isinstance(child, PackageEntry):
                continue
            meta = child.get_meta()
            if meta:
                yield key + '/', meta
            for child_key, child_meta in child._walk_dir_meta():
                yield key + '/' + child_key, child_meta

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
        meta.pop('top_hash', None)  # Obsolete as of PR #130
        pkg = cls()
        pkg._meta = meta
        for obj in reader:
            path = cls._split_key(obj.pop('logical_key'))
            subpkg = pkg._ensure_subpackage(path[:-1])
            key = path[-1]
            if not obj.get('physical_keys', None):
                # directory-level metadata
                subpkg.set_meta(obj['meta'])
                continue
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
        lkey = lkey.strip("/")
        root = self._ensure_subpackage(self._split_key(lkey)) if lkey else self

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
                entry = PackageEntry([f.as_uri()], f.stat().st_size, None, None)
                logical_key = f.relative_to(src_path).as_posix()
                # TODO: Warn if overwritting a logical key?
                root.set(logical_key, entry)
        elif url.scheme == 's3':
            src_bucket, src_key, src_version = parse_s3_url(url)
            if src_version:
                raise PackageException("Directories cannot have versions")
            if src_key and not src_key.endswith('/'):
                src_key += '/'
            objects, _ = list_object_versions(src_bucket, src_key)
            for obj in objects:
                if not obj['IsLatest']:
                    continue
                obj_url = 's3://%s/%s' % (src_bucket, quote(obj['Key']))
                if obj['VersionId'] != 'null':  # Yes, 'null'
                    obj_url += '?versionId=%s' % quote(obj['VersionId'])
                entry = PackageEntry([obj_url], None, None, None)
                logical_key = obj['Key'][len(src_key):]
                # TODO: Warn if overwritting a logical key?
                root.set(logical_key, entry)
        else:
            raise NotImplementedError

        return self

    def get(self, logical_key):
        """
        Gets object from local_key and returns its physical path.
        Equivalent to self[logical_key].get().

        Args:
            logical_key(string): logical key of the object to get

        Returns:
            Physical path as a string.

        Raises:
            KeyError: when logical_key is not present in the package
            ValueError: if the logical_key points to a Package rather than PackageEntry.
        """
        obj = self[logical_key]
        if not isinstance(obj, PackageEntry):
            raise ValueError("Key does point to a PackageEntry")
        return obj.get()

    def get_meta(self):
        """
        Returns user metadata for this Package.
        """
        return self._meta.get('user_meta', {})

    def set_meta(self, meta):
        """
        Sets user metadata on this Package.
        """
        self._meta['user_meta'] = meta

    def _fix_sha256(self):
        entries = [entry for key, entry in self.walk() if entry.hash is None]
        if not entries:
            return

        physical_keys = (entry.physical_keys[0] for entry in entries)
        total_size = sum(entry.size for entry in entries)
        results = calculate_sha256(physical_keys, total_size)

        for entry, obj_hash in zip(entries, results):
            entry.hash = dict(type='SHA256', value=obj_hash)

    def _set_commit_message(self, msg):
        """
        Sets a commit message.

        Args:
            msg: a message string

        Returns:
            None

        Raises:
            a ValueError if msg is not a string
        """
        if msg is not None and not isinstance(msg, str):
            raise ValueError("The package message must be a string.")

        self._meta.update({'message': msg})

    def build(self, name=None, registry=None, message=None):
        """
        Serializes this package to a registry.

        Args:
            name: optional name for package
            registry: registry to build to
                    defaults to local registry
            message: the commit message of the package

        Returns:
            the top hash as a string
        """
        self._set_commit_message(message)

        registry_prefix = get_package_registry(fix_url(registry) if registry else None)

        self._fix_sha256()

        hash_string = self.top_hash()
        manifest = io.BytesIO()
        self.dump(manifest)
        put_bytes(
            manifest.getvalue(),
            registry_prefix + '/packages/' + hash_string
        )

        if name:
            # Sanitize name.
            validate_package_name(name)

            named_path = registry_prefix + '/named_packages/' + quote(name) + '/'
            # todo: use a float to string formater instead of double casting
            hash_bytes = hash_string.encode('utf-8')
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
        writer = jsonlines.Writer(writable_file)
        for line in self.manifest:
            writer.write(line)

    @property
    def manifest(self):
        """
        Returns a generator of the dicts that make up the serialied package.
        """
        yield self._meta
        for dir_key, meta in self._walk_dir_meta():
            yield {'logical_key': dir_key, 'meta': meta}
        for logical_key, entry in self.walk():
            yield {'logical_key': logical_key, **entry.as_dict()}

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
                if entry is a string, it is treated as a URL, and an entry is created based on it
            meta(dict): user level metadata dict to attach to entry

        Returns:
            self
        """
        if isinstance(entry, (string_types, getattr(os, 'PathLike', str))):
            url = fix_url(str(entry))
            size, orig_meta = get_size_and_meta(url)
            entry = PackageEntry([url], size, None, orig_meta)
        elif isinstance(entry, PackageEntry):
            entry = entry._clone()
        else:
            raise TypeError("Expected a string for entry")
        if meta is not None:
            entry.set_user_meta(meta)

        path = self._split_key(logical_key)

        pkg = self._ensure_subpackage(path[:-1], ensure_no_entry=True)
        if path[-1] in pkg and isinstance(pkg[path[-1]], Package):
            raise QuiltException("Cannot overwrite directory with PackageEntry")
        pkg._children[path[-1]] = entry

        return self

    def _ensure_subpackage(self, path, ensure_no_entry=False):
        """
        Creates a package and any intermediate packages at the given path.

        Args:
            path(list): logical key as a list or tuple
            ensure_no_entry(boolean): if True, throws if this would overwrite
                a PackageEntry that already exists in the tree.

        Returns:
            newly created or existing package at that path
        """
        pkg = self
        for key_fragment in path:
            if ensure_no_entry and key_fragment in pkg \
                    and isinstance(pkg[key_fragment], PackageEntry):
                raise QuiltException("Already a PackageEntry along the path.")
            pkg = pkg._children.setdefault(key_fragment, Package())
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
        assert 'top_hash' not in self._meta
        top_meta = json.dumps(self._meta, sort_keys=True, separators=(',', ':'))
        top_hash.update(top_meta.encode('utf-8'))
        for logical_key, entry in self.walk():
            if entry.hash is None or entry.size is None:
                raise QuiltException("PackageEntry missing hash and/or size: %s" % entry.physical_keys[0])
            entry_dict = entry.as_dict()
            entry_dict['logical_key'] = logical_key
            entry_dict.pop('physical_keys', None)
            entry_dict_str = json.dumps(entry_dict, sort_keys=True, separators=(',', ':'))
            top_hash.update(entry_dict_str.encode('utf-8'))

        return top_hash.hexdigest()

    def push(self, name, dest, registry=None, message=None):
        """
        Copies objects to path, then creates a new package that points to those objects.
        Copies each object in this package to path according to logical key structure,
        then adds to the registry a serialized version of this package
        with physical_keys that point to the new copies.
        Args:
            name: name for package in registry
            dest: where to copy the objects in the package
            registry: registry where to create the new package
            message: the commit message for the new package
        Returns:
            A new package that points to the copied objects
        """
        validate_package_name(name)
        self._set_commit_message(message)

        if registry is None:
            registry = dest

        self._fix_sha256()

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
        pkg = self.__class__()
        pkg._meta = self._meta
        # Since all that is modified is physical keys, pkg will have the same top hash
        for logical_key, entry in self.walk():
            # Copy the datafiles in the package.
            physical_key = _to_singleton(entry.physical_keys)
            new_physical_key = dest_url + "/" + quote(logical_key)
            versioned_key = copy_file(physical_key, new_physical_key, entry.meta)

            # Create a new package entry pointing to the new remote key.
            new_entry = entry._clone()
            new_physical_key = versioned_key[0] if versioned_key else new_physical_key
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
        other_entries = dict(other_pkg.walk())
        for lk, entry in self.walk():
            other_entry = other_entries.pop(lk, None)
            if other_entry is None:
                deleted.append(lk)
            elif entry != other_entry:
                modified.append(lk)

        added = list(sorted(other_entries))
        
        return added, modified, deleted
