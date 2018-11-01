import copy
from enum import Enum
import hashlib
import io
import json
import pathlib
import os

import tempfile
import time

from urllib.parse import quote, urlparse

import jsonlines

from pathlib import Path
from .data_transfer import copy_file, deserialize_obj, download_bytes, TargetType, _guess_target_by_ext

from .exceptions import PackageException
from .util import HeliumException, BASE_PATH, fix_url, parse_file_url, parse_s3_url


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
    else:
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


class Package(object):
    """ In-memory representation of a package """

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

        registry = get_package_registry(fix_url(registry))

        if pkg_hash is not None:
            # if hash is specified, name doesn't matter
            pkg_path = '{}/packages/{}'.format(registry, pkg_hash)
            # TODO replace open with something that supports both local and s3
            pkg = self._from_path(pkg_path)
            # can't assign to self, so must mutate it
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
        # can't assign to self, so must mutate it
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

    @staticmethod
    def load(readable_file):
        """
        Loads a package from a readable file-like object.

        Args:
            readable_file: readable file-like object to deserialize package from

        Returns:
            a new package object

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
        Takes a package of a provided path.

        Recursively enumerates every file in path, and returns a new
        package that contains all those files.

        Args:
            path(string): path to package

        Returns:
            A new Package of that path

        Raises:
            when path doesn't exist
        """
        prefix = "" if not prefix else quote(prefix).strip("/") + "/"

        # TODO: anything but local paths
        # TODO: deserialization metadata
        src_path = pathlib.Path(path)
        files = src_path.rglob('*')
        pkg = self._clone()
        for f in files:
            if not f.is_file():
                continue
            entry = PackageEntry.from_local_path(f)
            logical_key = prefix + f.relative_to(src_path).as_posix()
            # TODO: Warn if overwritting a logical key?
            pkg = pkg.set(logical_key, entry)

        # modified package should have new top hash
        pkg._unset_tophash()
        return pkg

    def get(self, logical_key):
        """
        Gets object from logical_key and returns it as an in-memory object.

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

        target_str = entry.meta.get('target')
        if target_str is None:
            target_str = _guess_target_by_ext(logical_key, None)
            if target_str is None:
                # No ext for logical key -- let's check the physical keys.
                # to be safe, just use bytes if there's a conflict.
                targets = [_guess_target_by_ext(k, None) for k in entry.physical_keys]
                targets = [t for t in targets if t]
                if targets and all(t == targets[0] for t in targets):
                    # no conflicts -- use the found target type.
                    target_str = targets[0]
            if target_str is None:
                HeliumException("No serialization target in metadata, and inference failed.")
        try:
            target = TargetType(target_str)
        except ValueError:
            raise HeliumException("Unknown serialization target: %r" % target_str)

        physical_keys = entry.physical_keys
        if len(physical_keys) > 1:
            raise NotImplementedError
        physical_key = physical_keys[0] # TODO: support multiple physical keys

        data = read_physical_key(physical_key)

        # TODO: verify hash

        return deserialize_obj(data, target), entry.meta.get('user_meta')

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

    def build(self, name=None):
        """
        Serializes this package to a local registry.

        Args:
            name: optional name for package in registry
                    defaults to the textual hash of the package manifest

        Returns:
            the top hash as a string
        """
        hash_string = self.top_hash()["value"]
        with open(get_local_package_registry() / "packages" / hash_string, "w") as fh:
            self.dump(fh)

        if name:
            # Build the package directory if necessary.
            named_path = get_local_package_registry() / "named_packages" / name
            named_path.mkdir(parents=True, exist_ok=True)
            # todo: use a float to string formater instead of double casting
            with open(named_path / str(int(time.time())), "w") as fh:
                fh.write(self.top_hash()["value"])
            # todo: symlink when local
            with open(named_path / "latest", "w") as fh:
                fh.write(self.top_hash()["value"])
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
        self.top_hash() # assure top hash is calculated
        writer = jsonlines.Writer(writable_file)
        writer.write(self._meta)
        for logical_key, entry in self._data.items():
            writer.write({'logical_key': logical_key, **entry.as_dict()})

    def update(self, new_keys_dict, meta=None):
        """
        Returns a new package with the object at logical_key set to entry.

        If a metadata dict is provided, it is attached to and overwrites 
        metadata for all entries in new_keys_dict.

        Args:
            new_dict(dict): dict of logical keys to 
            meta(dict): metadata dict to attach to every input entry.

        Returns:
            A new package

        """
        pkg = self._clone()
        for logical_key, entry in new_keys_dict.items():
            pkg = pkg.set(logical_key, entry, meta)
        return pkg

    def set(self, logical_key, entry=None, meta=None):
        """
        Returns a new package with the object at logical_key set to entry.

        Args:
            logical_key(string): logical key to update
            entry(PackageEntry OR string): new entry to place at logical_key in the package
                if entry is a string, it is treated as a path to local disk and an entry
                is created based on the file at that path on your local disk
            meta(dict): metadata dict to attach to entry. If meta is provided, set just
                updates the meta attached to logical_key without changing anything
                else in the entry

        Returns:
            A new package
        """
        if entry is None and meta is None:
            raise PackageException('Must specify either entry or meta')

        if entry is None:
            return self._update_meta(logical_key, meta)

        pkg = self._clone()
        if isinstance(entry, str):
            entry = PackageEntry.from_local_path(entry)
            if meta is not None:
                entry.meta = meta
            pkg._data[logical_key] = entry
        elif isinstance(entry, PackageEntry):
            pkg._data[logical_key] = entry
            if meta is not None:
                raise PackageException("Must specify metadata in the entry")
        else:
            raise NotImplementedError
        
        # modified package should have new top hash
        pkg._unset_tophash()
        return pkg

    def _update_meta(self, logical_key, meta):
        pkg = self._clone()
        pkg._data[logical_key].meta = meta
        # modified package should have new top hash
        pkg._unset_tophash()
        return pkg

    def delete(self, logical_key):
        """
        Returns a new package with logical_key removed.

        Returns:
            A new package

        Raises:
            KeyError: when logical_key is not present to be deleted
        """
        pkg = self._clone()
        pkg._data.pop(logical_key)
        # modified package should have new top hash
        pkg._unset_tophash()
        return pkg

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
        return self._meta['top_hash']

    def push(self, name, path):
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
        dest = fix_url(path)
        if not dest.startswith('s3://'):
            raise NotImplementedError
        if not name:
            # todo: handle where to put data for unnamed remote packages
            raise NotImplementedError
        pkg = self._materialize('{}/{}'.format(dest.strip("/"), quote(name)))

        with tempfile.NamedTemporaryFile() as manifest:
            pkg.dump(manifest)
            manifest.flush()
            copy_file(
                pathlib.Path(manifest.name).resolve().as_uri(),
                get_package_registry(path) + "/packages/" + pkg.top_hash()["value"],
                {}
            )

        if name:
            # Build the package directory if necessary.
            named_path = get_package_registry(path) + '/named_packages/' + name + "/"
            # todo: use a float to string formater instead of double casting
            with tempfile.NamedTemporaryFile() as hash_file:
                hash_file.write(pkg.top_hash()["value"].encode('utf-8'))
                hash_file.flush()
                copy_file(
                    pathlib.Path(hash_file.name).resolve().as_uri(),
                    named_path + str(int(time.time())),
                    {}
                )
                hash_file.seek(0)
                copy_file(
                    pathlib.Path(hash_file.name).resolve().as_uri(),
                    named_path + "latest",
                    {}
                )
        return pkg

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
