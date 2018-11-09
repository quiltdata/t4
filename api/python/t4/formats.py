#! /usr/bin/python
# -*- coding: utf-8 -*-

""" formats.py

This module handles binary formats, and conversion to/from objects.

# Formats Class (plural)

The `Formats` class acts as a global container for registered formats,
and provides a place to register and discover formats.

    * metadata
    * file extension
    * serializable object

..as well as other types in the future, potentially.

Format objects are registered with the Formats class by calling
`Formats.register(format_obj)`, or `Formats.register(**new_format_args)`.


# Format Class (singular)

A Format has, at bare minimum:
    * a name specific to the format used (NOT to the format object used)
      * I.e., two Format objects that both handle JSON should both be
        named 'json'
    * a serializer
    * a deserializer

Aside from that, a format *should* have:
    * a list of filename extensions it can (theoretically) handle
    * a list of object types it can handle

Format objects can be registered directly by calling "f.register()".
"""

### Python imports
from collections import (
    defaultdict,
    OrderedDict,
    )
import io
import json

### Third Party imports
from six import text_type

### Project imports
from .util import package_exists, QuiltException

### Constants


### Code
class Formats:
    """A collection for organizing `Format` objects.

    This class organizes `Format` objects for querying and general use.
    It provides methods for querying by format name, metadata dict, handled
    extensions, or handled object types.  This list may expand in the future,
    so see the actual class methods.
    """
    registered_formats = OrderedDict()
    formats_by_ext = defaultdict(list)
    # latest adds are last, and come first in lookups by type via `for_obj`.
    def __init__(self):
        raise TypeError("The {!r} class is organizational, and cannot be instantiated."
                        .format(type(self).__name__))

    @classmethod
    def _register_by_format(cls, format):
        cls.registered_formats[format.name] = format
        for ext in format._handled_extensions:
            cls.formats_by_ext[ext.lower().strip('. ')].insert(0, format)

    @classmethod
    def register(cls, name_or_format, serializer=None, deserializer=None, handled_extensions=None,
                 handled_types=None):
        """Register a format for automatic usage

        If a `Format` object is given for `name_or_format`, it is registered
        directly and other args are ignored.

        If a `str` is given for `name_or_format`, it is used as the name of a
        new format, and `serializer` and `deserializer` are required.

        Args:
            See creation args for `Format` for complete usage args.
        """
        if isinstance(name_or_format, Format):
            return cls._register_by_format(name_or_format)
        cls._register_by_format(Format(
            name_or_format,
            serializer=serializer,
            deserializer=deserializer,
            handled_extensions=handled_extensions,
            handled_types=handled_types
        ))

    @classmethod
    def serialize(cls, obj, meta):
        # try to retain their meta-configured format.
        meta_fmt = cls.for_meta(meta)
        obj_fmts = cls.for_obj(obj, single=False)
        if meta_fmt in obj_fmts:
            assert isinstance(meta_fmt, Format)
            return meta_fmt.serialize(obj, meta=meta)
        elif obj_fmts:
            return obj_fmts[0].serialize(obj, meta=meta)
        else:
            raise QuiltException("No Format to serialize object with")

    @classmethod
    def deserialize(cls, bytes, meta=None, ext=None):
        meta_fmt = cls.for_meta(meta)
        if meta_fmt:
            assert isinstance(meta_fmt, Format)
            return meta_fmt.deserialize(bytes, meta=meta)
        ext_fmt = cls.for_ext(ext)
        if ext_fmt:
            return ext_fmt.deserialize(bytes, meta=meta)
        raise QuiltException("No serialization metadata, and guessing by extension failed.")

    @classmethod
    def match(cls, name):
        """Match a format by exact name."""
        return cls.registered_formats.get(name)

    @classmethod
    def for_ext(cls, ext, single=True):
        """Match a format (or formats) by extension."""
        ext = ext.lower().strip('. ')
        if single:
            matching_formats = cls.formats_by_ext[ext]
            return matching_formats[0] if matching_formats else None
        return cls.formats_by_ext[ext][:]

    @classmethod
    def for_obj(cls, obj, single=True):
        """Match a format (or formats) by a (potentially) serializable object"""
        if single:
            for format in reversed(cls.registered_formats.values()):
                if format.handles_obj(obj):
                    return format
            return
        return [format for format in reversed(cls.registered_formats.values()) if format.handles_obj(obj)]

    @classmethod
    def for_meta(cls, meta, single=True):
        """Match a format (or formats) by the given metadata"""
        # currently, this only finds one format.  We'll need to think
        # about people wanting more than one format handler for a particular
        # format.  ..someday.  ..maybe.
        name = None
        if 'format' in meta:
            name = meta['format'].get('name')
        if not name:
            name = meta.get('target')
        fmt = cls.registered_formats.get(name)
        if single:
            return fmt
        return [fmt] if fmt else []


class Format:
    """Binary format handler for serialization

    This is a generic type that can be instantiated directly with a
    serializer and deserializer for simple cases, or subclassed for
    more complex cases that require special attention or metadata
    handling.
    """
    def __init__(self, name, serializer=None, deserializer=None, handled_extensions=None, handled_types=None):
        """Create a new `Format` object

        Args:
            name(str): Name of new format to create.  Use existing name
                if your format is compatible with existing formats, if
                practicable.

            serializer(function): serializer function for new format
            deserializer(function): deserializer for new format

            handled_extensions(list(str)): a list of filename extensions
                that can be deserialized by this format

            handled_types: a list of types that can be serialized by this
                format
        """
        if name is None:
            raise TypeError("`name` is a required parameter.")
        self.name = name
        if serializer:
            self._serializer = serializer
        if deserializer:
            self._deserializer = deserializer

        if not (getattr(self, '_serializer', None) or (self.serialize != Format.serialize)):
            raise TypeError("A serializer is required.")
        if not (getattr(self, '_deserializer', None) or (self.deserialize != Format.deserialize)):
            raise TypeError("A deserializer is required.")

        self._handled_extensions = [] if handled_extensions is None else handled_extensions
        self._handled_types = [] if handled_types is None else handled_types

    def handles_ext(self, ext):
        """Check if this format handles the filetype indicated by an extension

        Args:
            ext: extension to check

        Returns:
            bool
        """
        exts = [e.lstrip().lower() for e in self._handled_extensions]
        return ext.lstrip('.').lower() in exts

    def handles_obj(self, obj):
        """Check if this format can serialize a given object.

        Args:
            obj: object to check

        Returns:
            bool
        """
        # naive -- doesn't handle subtypes for dicts, lists, etc.
        for typ in self._handled_types:
            if isinstance(obj, typ):
                return True
        return False

    def register(self):
        """Register this format for automatic usage

        Once registered, a format can be looked up by name, handled object
        types, and handled filetypes as indicated by extension.
        """
        Formats.register(self)

    def _update_meta(self, meta, serialization_kwargs={}):
        if meta is not None:
            format_meta = meta.get('format', {})
            format_meta['name'] = self.name

            if serialization_kwargs:
                format_meta['serialization'] = deepcopy(serialization_kwargs)
            meta['format'] = format_meta
            # todo: can we switch to a 'format' section rather than 'target' name?
            meta['target'] = self.name

    def serialize(self, obj, meta=None, **kwargs):
        """Serialize an object using this format

        Serializes `obj` using this format.  If `meta` is given, it is
        updated at meta['format']['name'] and (for now) meta['target'].

        If **kwargs are given, they are passed on to the serialization
        function, and are added to meta['target']['serialization'].

        One of the benefits of this is that once a serialization quirk has
        been used via **kwargs, the same args are used when updating with
        the same metadata.

        This is a wrapper for lower-level serializers like `dumps` methods.
        If overridden and then called via super(), it does nothing.

        Args:
            obj: object to serialize
            meta: metadata to update
            **kwargs: kwargs to send to lower-level serializer. Also included in meta
        """
        # deactivated if this method is overridden.
        if type(self).serialize == Format.serialize:
            # Method not overridden, so we use the configured one
            if getattr(self, '_serializer', None) is None:
                raise NotImplementedError()
            serialized = self._serializer(obj, **kwargs)
            self._update_meta(meta, kwargs)
            return serialized

    def deserialize(self, bytes_obj, meta=None, **kwargs):
        """Deserialize some bytes using this format

        Converts bytes into an object.

        If `meta['format']['deserialization']` is given, it is passed as
        kwargs to the lower-level deserializer.

        If **kwargs is given, it overrides metadata kwargs, if present.

        Args:
            bytes_obj: bytes to deserialize
            meta: object metadata, may contain deserialization prefs
            **kwargs: metadata to (potentially) use.
        """
        # deactivated if this method is overridden.
        if type(self).deserialize == Format.deserialize:
            meta = {} if meta is None else meta
            if getattr(self, '_deserializer', None) is None:
                raise NotImplementedError()
            format_meta = meta.get('format', {})
            deserialization_kwargs = format_meta.get('deserialization', {})
            deserialization_kwargs.update(kwargs)
            return self._deserializer(bytes_obj, **deserialization_kwargs)


Formats.register('bytes',
    serializer=lambda obj: obj,
    deserializer=lambda bytes_obj: bytes_obj,
    handled_extensions=['bin'],
    handled_types=[bytes],
)


Formats.register('json',
    serializer=lambda obj, **kwargs: json.dumps(obj, **kwargs).encode('utf-8'),
    deserializer=lambda bytes_obj, **kwargs: json.loads(bytes_obj.decode('utf-8'), **kwargs),
    handled_extensions=['json'],
    handled_types=[dict, list, int, float, str]
)


Formats.register('unicode',  # utf-8 instead?
    serializer=lambda s: s.encode('utf-8'),
    deserializer=lambda b: b.decode('utf-8'),
    handled_extensions=['txt', 'md', 'rst'],
    handled_types=[text_type],
)


class NumpyFormat(Format):
    def __init__(self, name, handled_extensions=None, **kwargs):
        handled_extensions = [] if handled_extensions is None else handled_extensions

        # don't include these extensions unlss numpy is present.
        if package_exists('numpy'):
            if 'npy' not in handled_extensions:
                handled_extensions.append('npy')
            if 'npz' not in handled_extensions:
                handled_extensions.append('npz')

        super().__init__(name, handled_extensions=handled_extensions, **kwargs)

    def handles_obj(self, obj):
        # don't load numpy until we actually have to use it..
        if package_exists('numpy'):
            import numpy as np
            if np.ndarray not in self._handled_types:
                self._handled_types.append(np.ndarray)
        return super().handles_obj(obj)

    def _deserializer(self, bytes_obj):
        import numpy as np

        buf = io.BytesIO(bytes_obj)
        return np.load(buf, allow_pickle=False)

    def _serializer(self, obj):
        import numpy as np
        buf = io.BytesIO()
        np.save(buf, obj, allow_pickle=False)
        return buf.getvalue()


if package_exists('numpy'):
    NumpyFormat('numpy').register()


class ParquetFormat(Format):
    def __init__(self, name, handled_extensions=None, **kwargs):
        handled_extensions = [] if handled_extensions is None else handled_extensions

        if package_exists('pyarrow') and package_exists('pandas'):
            handled_extensions.append('parquet')
        super().__init__(name, handled_extensions=handled_extensions, **kwargs)

    def handles_obj(self, obj):
        # don't load pyarrow or pandas unless we actually have to use them..
        if package_exists('pyarrow') and package_exists('pandas'):
            import pandas as pd
            self._handled_types.append(pd.DataFrame)
        return super().handles_obj(obj)

    def _deserializer(self, bytes_obj):
        import pyarrow as pa
        from pyarrow import parquet

        buf = io.BytesIO(bytes_obj)
        table = parquet.read_table(buf)
        try:
            obj = pa.Table.to_pandas(table)
        except AssertionError:
            # Try again to convert the table after removing
            # the possibly buggy Pandas-specific metadata.
            # XXX: Can we detect this during serialization and store it separately?
            meta = table.schema.metadata.copy()
            meta.pop(b'pandas')
            newtable = table.replace_schema_metadata(meta)
            obj = newtable.to_pandas()
        return obj

    def _serializer(self, obj):
        import pyarrow as pa
        from pyarrow import parquet
        buf = io.BytesIO()
        table = pa.Table.from_pandas(obj)
        parquet.write_table(table, buf)
        return buf.getvalue()

if package_exists('pyarrow') and package_exists('pandas'):
    ParquetFormat('pyarrow', handled_extensions=['parquet']).register()

