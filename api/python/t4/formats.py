""" formats.py

This module handles binary formats, and conversion to/from objects.

# FormatsRegistry Class (plural)

The `FormatsRegistry` class acts as a global container for registered formats,
and provides a place to register and discover formats.

    * metadata
    * file extension
    * serializable object

..as well as other types in the future, potentially.

Format objects are registered with the FormatsRegistry class by calling
`FormatsRegistry.register(format_obj)`, or `FormatsRegistry.register(**new_format_args)`.


# Format Class (singular)

A Format is tied to *logical key* metadata.
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

# Format metadata
In an object's metadata, the format should only touch the 'format' key,
and possibly the 'target' key.

Format metadata has the following form:

```
{
  # name is a unique format name, like csv, json, parquet, numpy, etc
  'name': <format name>,
  # opts are options to help with serialization / deserialization.  These are
  # needed when a format is leaky or ill-defined, as is the case with CSV
  'opts': {<opt name>: <opt value>}  # opt must be present in cls.opts to be used.
}

"""

# Python imports
from abc import ABC, abstractmethod
from collections import (
    defaultdict,
    OrderedDict,
    Mapping,
    )
import copy
import csv
import io
import json
import sys

# Third Party imports
from six import text_type

# Project imports
from .util import QuiltException

# Constants
class NOT_SET:
    """Used as an indicator of disuse when `None` is a valid value"""
    def __init__(self):
        raise RuntimeError("Not an instantiable class.")


# Code
class FormatRegistry:
    """A collection for organizing `Format` objects.

    This class organizes `Format` objects for querying and general use.
    It provides methods for querying by format name, metadata dict, handled
    extensions, or handled object types.  This list may expand in the future,
    so see the actual class methods.
    """
    registered_formats = list()

    # latest adds are last, and come first in lookups by type via `for_obj`.
    def __init__(self):
        raise TypeError("The {!r} class is organizational, and cannot be instantiated."
                        .format(type(self).__name__))

    @classmethod
    def register(cls, format):
        formats = cls.registered_formats

        # no duplicates, just reprioritize.
        if format in formats:
            formats.pop(formats.index(format))

        formats.insert(0, format)

    @classmethod
    def serialize(cls, obj, meta=None, ext=None, raw_args=None, check_only=False, **format_opts):
        # try to retain their meta-configured format.
        meta_fmt = cls.for_meta(meta)
        ext_fmts = cls.for_ext(ext, single=False)
        obj_fmts = cls.for_obj(obj, single=False)

        if meta_fmt:
            # meta_fmt should always be an exact match on what to use.
            if meta_fmt not in obj_fmts:
                raise QuiltException("Metadata specified the {!r} format, but it doesn't handle {!r} objects."
                                     .format(meta_fmt.name, type(obj)))
            # Warn about a known, definitive extension / metadata format mismatch.
            if ext_fmts and meta_fmt not in ext_fmts and not check_only:
                print("Notice: Using format specified by metadata ({!r}) but extension {!r} doesn't match."
                      .format(meta_fmt.name, ext))
            assert isinstance(meta_fmt, BaseFormat)
            return (meta_fmt if check_only
                    else meta_fmt.serialize(obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts))
        # prefer a format that matches the extension.
        elif ext_fmts:
            for fmt in ext_fmts:
                if fmt in obj_fmts:
                    return (fmt if check_only
                            else fmt.serialize(obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts))
        # otherwise, just use the first format that can handle obj.
        if obj_fmts:
            if ext and not check_only:
                print("Notice: No matching serialization formats for extension {!r} with given object."
                      .format(ext))
                print("        Using {!r} format instead.".format(obj_fmts[0].name))
            fmt = obj_fmts[0]
            return (fmt if check_only
                    else fmt.serialize(obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts))
        raise QuiltException("No Format to serialize object with")

    @classmethod
    def deserialize(cls, bytes_obj, meta=None, ext=None, as_type=None, raw_args=None, check_only=False, **format_opts):
        meta_fmt = cls.for_meta(meta)
        ext_fmts = cls.for_ext(ext, single=False)
        typ_fmts = cls.for_type(as_type, single=False)

        # metadata is always an exact specification (if present)
        if meta_fmt:
            if as_type:
                if meta_fmt not in typ_fmts:
                    raise QuiltException("Cannot deserialize as specified type: {}".format(as_type))
            if check_only:
                return meta_fmt
            assert isinstance(meta_fmt, BaseFormat)
            return meta_fmt.deserialize(bytes_obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts)
        fmt_name = cls._get_name_from_meta(meta)
        if fmt_name:
            raise QuiltException("Metadata specified the {!r} format, which isn't registered."
                                 .format(fmt_name))
        # Try by extension
        for ext_fmt in ext_fmts:
            if as_type and ext_fmt not in typ_fmts:
                continue
            if check_only:
                return ext_fmt
            assert isinstance(ext_fmt, BaseFormat)
            return ext_fmt.deserialize(bytes_obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts)
        if ext_fmts and as_type:
            raise QuiltException("Cannot deserialize as specified type: {}".format(as_type))
        raise QuiltException("No serialization metadata, and guessing by extension failed.")

    @classmethod
    def match(cls, name):
        """Match a format by exact name."""
        for fmt in cls.registered_formats:
            if fmt.name == name:
                return fmt

    @classmethod
    def for_ext(cls, ext, single=True):
        """Match a format (or formats) by extension."""
        if not ext:
            return None if single else []
        ext = ext.lower().strip('. ')
        matching_formats = []
        for fmt in cls.registered_formats:
            if fmt.handles_ext(ext):
                if single:
                    return fmt
                matching_formats.append(fmt)
        return matching_formats

    @classmethod
    def for_type(cls, typ, single=True):
        """Match a format (or formats) by a (potentially) serializable type"""
        if typ is None:
            return None if single else []

        matching_formats = []

        for fmt in cls.registered_formats:
            if fmt.handles_type(typ):
                if single:
                    return fmt
                matching_formats.append(fmt)
        return matching_formats

    @classmethod
    def for_obj(cls, obj, single=True):
        """Match a format (or formats) by a (potentially) serializable object"""
        return cls.for_type(type(obj), single=single)

    @classmethod
    def _get_name_from_meta(cls, meta):
        name = meta.get('format', {}).get('name')
        # 'target': compat with older pkg structure -- can probably be removed soon.
        if not name:
            name = meta.get('target')
        return name

    @classmethod
    def for_meta(cls, meta):
        """Unambiguously match a specific format by the given metadata"""
        # As a point of order, this must return a singular format.
        name = cls._get_name_from_meta(meta)
        fmt = cls.match(name)
        return fmt


class BaseFormat(ABC):
    """Base class for binary format handlers
    """
    opts = tuple()
    name = None
    handled_extensions = tuple()
    handled_types = tuple()

    def __init__(self, name=None, handled_extensions=tuple(), handled_types=tuple()):
        """Common initialization for BaseFormat subclasses
        
        Subclasses implement the `serialize()` and `deserialize()` methods,
        which are passed the object/bytes to handle, as well as metadata and
        runtime kwargs.
        
        Subclasses *may* implement custom `handles_ext`, `handles_type` methods
        if there is a scenario which requires it (such as lazy load of a large
        module).

        Subclasses *may* define a class-level tuple named `opts`.  This tuple
        is used to name options that should be retained in metadata for the
        purpose of serialization/deserialization.  A subclass may process the
        options before using them, to vet them for security -- however, options
        which can potentially cause security issues should be avoided
        altogether.  `cls.opts` are useful to handle quirks in poorly-defined
        formats, such as CSV, TSV, and similar.
        
        Args:
            name(str): Name of new format.  Use existing name if your
                format is compatible with existing formats, if practicable.  
                I.e., two different CSV format handlers should both use 'csv'.

            handled_extensions(iterable(str)): filename extensions that can be
                deserialized by this format

            handled_types(iterable(type)): types that can be serialized to
                (and deserialized from) by this format
        """
        self.name = name if name else self.name
        if not self.name:
            raise TypeError("No `name` attribute has been defined for {!r}".format(type(self).__name__))

        # add user extensions if given
        self.handled_extensions = set(ext.lstrip('.').lower() for ext in self.handled_extensions)
        self.handled_extensions.update(ext.lstrip('.').lower() for ext in handled_extensions)

        # add user types if given
        self.handled_types = set(self.handled_types) | set(handled_types)

    def handles_ext(self, ext):
        """Check if this format handles the filetype indicated by an extension

        Args:
            ext: extension to check

        Returns:
            bool
        """
        return ext.lstrip('.').lower() in self.handled_extensions

    def handles_type(self, typ):
        """Check if this format can serialize a given object.

        Args:
            obj: object to check

        Returns:
            bool
        """
        for handled_type in self.handled_types:
            if issubclass(typ, handled_type):
                return True
        return False

    def register(self):
        """Register this format for automatic usage

        Once registered, a format can be looked up by name, handled object
        types, and handled filetypes as indicated by extension.
        """
        FormatRegistry.register(self)

    def _update_meta(self, meta, additions=None):
        """Merge `additions` into a copy of `meta`, and returns the result.

        `additions` are recursively merged into `meta`.  If a .
        """
        additions = additions if additions else {}
        meta = copy.deepcopy(meta) if meta is not None else {}

        format_meta = meta.get('format', {})
        meta['format'] = format_meta   # in case default was used

        if additions:
            format_meta.update(additions)

        format_meta['name'] = self.name

        # compat -- remove once we stop using 'target' in other code.
        meta['target'] = self.name

        return meta

    @abstractmethod
    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        """Serialize an object using this format

        Args:
            obj: object to serialize
            meta: metadata to update
            raw_args: passed directly to serializer, and not retained in
                metadata.  Be cautious when using this, as the args are not
                retained.
            **format_opts: Format options retained in metadata.  These are
                needed for some poorly-specified formats, like CSV.  If
                used in serialization, they are retained and used for
                deserialization.
        Returns:
            (bytes, dict):
                bytes: serialized object
                dict: metadata update
        """
        pass

    @abstractmethod
    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        """Deserialize some bytes using this format

        Converts bytes into an object.

        If **kwargs is given, the kwargs are passed to the deserializer.

        Args:
            bytes_obj: bytes to deserialize
            meta: object metadata, may contain deserialization prefs
            raw_args: passed directly to deserializer, and not retained in
                metadata.
            **format_opts: Format options retained in metadata.  These are
                needed for some poorly-specified formats, like CSV.  If
                used in serialization, they are retained and used for
                deserialization.
        Returns:
            object
        """
        pass

    def __repr__(self):
        return "<{} {!r}, handling exts {} and types {}>".format(
            type(self).__name__,
            self.name,
            sorted(self.handled_extensions),
            sorted(t.__name__ for t in self.handled_types),
        )

    def get_opts(self, meta, user_opts=None):
        """Get options from format_opts or meta.

        This drops or rejects any options that are not named in self.opts.

        Args:
              user_opts(dict):  Format options from the user.  Used if given,
                and an error is raised for any invalid arguments.
              meta(dict):  Object metadata.  Used if user_opts is not given,
                and invalid options are dropped.
        """
        allowed = set(self.opts)
        if user_opts:
            assert isinstance(user_opts, Mapping)
            for name in user_opts:
                if name not in allowed or not isinstance(name, str):
                    raise QuiltException("Invalid option: {!r}".format(name))
            return copy.deepcopy(user_opts)
        meta = meta if meta else {}
        meta_opts = meta.get('format', {}).get('opts', {})

        return {name: meta_opts[name] for name in allowed
                if name in meta_opts
                and isinstance(name, str)}


class GenericFormat(BaseFormat):
    """Generic format for handling simple serializer/deserializer pairs

    This is a generic type that can be instantiated directly, passing in
    a 'serializer' and 'deserializer'.  See 'name' for the format name.
    """
    def __init__(self, name, handled_extensions, handled_types, serializer, deserializer):
        super().__init__(name, handled_extensions, handled_types)

        assert callable(serializer) and callable(deserializer)
        self._serializer, self._deserializer = serializer, deserializer

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        """Pass `obj` to serializer and update `meta`, returning the result

        `meta` is only updated if serialization succeeds without error.

        Args:
            obj(object): object to serialize
            meta(dict): dict of associated metadata to update
            ext: File extension -- used f.e. when metadata is missing
            raw_args: passed directly to serializer, and not retained in
                metadata.  Be cautious when using this, as the args are not
                retained.
            **format_opts: Format options retained in metadata.  These are
                needed for some poorly-specified formats, like CSV.  If
                used in serialization, they are retained and used for
                deserialization.
        Returns:
            `obj` encoded as `bytes`
            :param raw_args:
        """
        data = self._serializer(obj, **(raw_args if raw_args else {}))
        return data, self._update_meta(meta)

    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        """Pass `bytes_obj` to deserializer and return the result

        Args:
            bytes_obj(bytes): bytes to deserialize
            meta(dict): ignored for GenericFormat formats
            **kwargs: passed directly to deserializer
        """
        return self._deserializer(bytes_obj, **(raw_args if raw_args else {}))


GenericFormat(
    'bytes',
    serializer=lambda obj: obj,
    deserializer=lambda bytes_obj: bytes_obj,
    handled_extensions=['bin'],
    handled_types=[bytes],
).register()


GenericFormat(
    'json',
    serializer=lambda obj, **kwargs: json.dumps(obj, **kwargs).encode('utf-8'),
    deserializer=lambda bytes_obj, **kwargs: json.loads(bytes_obj.decode('utf-8'), **kwargs),
    handled_extensions=['json'],
    handled_types=[dict, list, int, float, str, tuple, type(None)]
).register()


# compatibility with prior code.  The 'utf-8' GenericFormat supersedes this,
# as it is loaded after this, but this is still present to decode existing stored objects.
GenericFormat(
    'unicode',
    serializer=lambda s: s.encode('utf-8'),
    deserializer=lambda b: b.decode('utf-8'),
    handled_extensions=['txt', 'md', 'rst'],
    handled_types=[text_type],
).register()


GenericFormat(
    'utf-8',  # utf-8 instead?
    serializer=lambda s: s.encode('utf-8'),
    deserializer=lambda b: b.decode('utf-8'),
    handled_extensions=['txt', 'md', 'rst'],
    handled_types=[text_type],
).register()


class CSVPandasFormat(BaseFormat):
    """Format for Pandas DataFrame <--> CSV formats

    Format Opts:
        The following options may be used anywhere format opts are accepted,
        or directly in metadata under `{'format': {'opts': {...: ...}}}`.

        doublequote(bool, default True): if quotechars are used, interpret two
            inside a field as a single quotechar element
        encoding(str): name of encoding used, default 'utf-8'
        escapechar(str length 1, default None):
            one-char string used to escape delimiter when quoting is "none"
        fieldsep(str): string that separates fields.
            serialization: default is ','
            deserialization: default is to detect automatically
        header_names(list):
            Use this if you want to store column names in metadata instead of
            in a header row.  To stop using these, you'll need to later set

            serializing: If headers are used, use these names instead of
                the DataFrame column names.
            deserializing: Use these names as the column names.
                If `use_header` is True: header is dropped
                If `use_header` is False: no header is read
                In either case, `header_names` will define the column names.
        index_names(list of str or int):
            If given, these are stored in T4 metadata.  The names are used
            instead of existing/configured index column names (if any).

            serializing: The list must be the same length as the number of
                indexes.  Given names are used instead of DataFrame index
                names.
            deserializing:
                Default behavior:
                    The list length indicates the number of indexes.  The
                    names given are used for those indexes.
                Alternate behavior: See `index_names_are_keys`.
        index_names_are_keys(bool, default False):
            If True:
                When deserializing, `index_names` indicate column name or
                column index to use as index/multi-index (in order).  If the
                column name or index isn't present, deserialization fails.
            If False (default): When deserializing, index_names indicate the
                names to use for the first columns, and to use those columns
                as an index/multi-index.
        linesep(str):
            Line separator
        na_values(list of str): Default: ['', '#N/A', '#N/A N/A', '#NA',
                '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN',
                'N/A', 'NA', 'NULL', 'NaN', 'n/a', 'nan', 'null']
            serialization:
                the first value is used to indicate a null/missing value. ''
                if not given.
            deserialization:
                The values given are treated as null/None.  If nothing is set,
                defaults are used.
        quotechar(str len 1):
            The character used to denote the beginning and end of a quoted
            item.
        quoting(str):
            Only useful when serializing.  Options are 'all', 'minimal',
            'none', and 'nonnumeric'.
        skip_spaces(bool):
            If True: Skip spaces immediately following fieldsep.
            If False (default): Treat spaces after fieldsep as data
        use_header(bool):
            If True (default):
                Include header when serializing, and expect one when
                deserializing.
            If False:
                Exclude header when serializing, and don't expect one when
                deserializing.
        use_index(bool):
            If True(default):
                Include indexes when serializing, and expect them when
                deserializing.
            If False:
                Exclude indexes when serializing, and don't expect them when
                deserializing.
    """
    name = 'csv'
    handled_extensions = ['csv', 'tsv', 'ssv']
    opts = ('doublequote', 'encoding', 'escapechar', 'fieldsep', 'header_names', 'index_names',
            'index_names_are_keys', 'linesep', 'na_values', 'quotechar', 'quoting', 'skip_spaces', 'use_header',
            'use_index')
    # defaults shouldn't be added to metadata, just used directly.
    defaults = {
        'encoding': 'utf-8',
        'index_names_are_keys': False,
        'na_values': ['', '#N/A', '#N/A N/A', '#NA',
            '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN',
            'N/A', 'NA', 'NULL', 'NaN', 'n/a', 'nan', 'null'],
        'use_header': True,
        'use_index': False,
    }

    def handles_type(self, typ):
        # don't load pandas unless we actually have to use it..
        if 'pandas' not in sys.modules:
            return False
        import pandas as pd

        self.handled_types.add(pd.DataFrame)

        return super().handles_type(typ)

    def _quoting_opt_to_python(self, value):
        if isinstance(value, int):
            return value
        elif isinstance(value, str):
            value = value.strip().lower()
            map = {
                'all': csv.QUOTE_ALL,
                'minimal': csv.QUOTE_MINIMAL,
                'none': csv.QUOTE_NONE,
                'nonnumeric': csv.QUOTE_NONNUMERIC
            }
            return map.get(value, NOT_SET)
        print("Unrecognized value for 'quoting' option: {!r}".format(value))
        return NOT_SET

    def get_ser_kwargs(self, opts):
        opts = copy.deepcopy(opts)
        result_kwargs = {}

        # interdependent opts, can't be processed individually.
        use_header = opts.pop('use_header')    # must exist, at least as a default
        header_names = opts.pop('header_names', None)
        if use_header:
            result_kwargs['header'] = header_names if header_names else True
        else:
            result_kwargs['header'] = False

        # No kwarg correlate for serialization
        opts.pop('index_names_are_keys', None)

        name_map = {
            'fieldsep': 'sep',
            'linesep': 'line_terminator',
            'use_index': 'index',
            'index_names': 'index_label',
        }
        for name, value in opts.items():
            if name in name_map:
                result_kwargs[name_map[name]] = value
            elif name == 'quoting':
                value = self._quoting_opt_to_python(value)
                if value is NOT_SET:
                    continue
                result_kwargs[name] = value
                continue
            elif name == 'na_values':
                result_kwargs['na_rep'] = value[0]
            else:
                # exact match / pass through arg
                result_kwargs[name] = value

        return result_kwargs


    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        opts = self.get_opts(meta, format_opts)

        default_opts = copy.deepcopy(self.defaults)

        # Use the default delimiter for the given extension, if no fieldsep was specified.
        if ext and 'fieldsep' not in opts:
            ext = ext.strip().lstrip('.').lower()
            ext_map = {'csv': ',', 'tsv': '\t', 'ssv': ';'}
            if ext in ext_map:
                default_opts['fieldsep'] = ext_map[ext]
        opts_with_defaults = default_opts
        opts_with_defaults.update(opts)

        # interdependent opts, can't be processed individually.
        # Does nothing during serialization, but we should check it at least makes sense.
        index_names_are_keys = opts_with_defaults.get('index_names_are_keys')
        if index_names_are_keys:
            if 'index_names' not in opts:
                raise QuiltException(
                    "Format option 'index_names_are_keys' is set, but 'index_names' not given."
                )
            elif not len(opts['index_names']) == len(obj.index.names):
                raise ValueError(
                    "{} entries in `index_names`, but the DataFrame to be serialized has {} indexes"
                    .format(len(opts['index_names']), len(obj.index.names))
                )

        kwargs = self.get_ser_kwargs(opts_with_defaults)
        buf = io.BytesIO()

        # pandas bug workaround -- see _WriteEncodingWrapper definition
        encoded_buf = self._WriteEncodingWrapper(buf, encoding=kwargs['encoding'])
        obj.to_csv(encoded_buf, **(raw_args if raw_args is not None else kwargs))

        return buf.getvalue(), self._update_meta(meta, additions={'opts': opts_with_defaults})

    def get_des_kwargs(self, opts):
        opts = copy.deepcopy(opts)
        result_kwargs = {}

        # Interdependent opts.
        header_names = opts.pop('header_names', None)
        use_header = opts.pop('use_header')  # opt should be present from defaults.
        if use_header:
            result_kwargs['header'] = 0
            if header_names:
                result_kwargs['names'] = header_names
        else:
            result_kwargs['header'] = None
            result_kwargs['names'] = header_names

        # Interdependent opts.
        index_names = opts.pop('index_names', None)
        use_index = opts.pop('use_index')   # opt should be present from defaults.
        index_names_are_keys = opts.pop('index_names_are_keys', False)
        if use_index:
            if index_names:
                if index_names_are_keys:
                    result_kwargs['index_col'] = index_names
                else:
                    result_kwargs['index_col'] = list(range(len(index_names)))
            else:
                result_kwargs['index_col'] = [0]
        else:
            result_kwargs['index_col'] = False

        # map names to pandas `df.to_csv() args`
        name_map = {
            'fieldsep': 'sep',
            'linesep': 'lineterminator',
        }
        for name, value in opts.items():
            if name == 'quoting':
                result_kwargs[name] = self._quoting_opt_to_python(value)
            elif name in name_map:
                result_kwargs[name_map[name]] = value
            else:
                # exact match / passthrough arg
                result_kwargs[name] = value

        return result_kwargs

    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        import pandas as pd     # large import / lazy

        opts = self.get_opts(meta, format_opts)
        default_opts = copy.deepcopy(self.defaults)

        # Use the default delimiter for the given extension, if no fieldsep was specified.
        if ext and 'fieldsep' not in opts:
            ext = ext.strip().lstrip('.').lower()
            ext_map = {'csv': ',', 'tsv': '\t', 'ssv': ';'}
            if ext in ext_map:
                default_opts['fieldsep'] = ext_map[ext]
        opts_with_defaults = default_opts
        opts_with_defaults.update(opts)

        kwargs = self.get_des_kwargs(opts_with_defaults)
        df = pd.read_csv(io.BytesIO(bytes_obj), **(raw_args if raw_args else kwargs))

        index_names = opts_with_defaults.get('index_names')
        index_names_are_keys = opts_with_defaults.get('index_names_are_keys')
        if index_names and not index_names_are_keys:
            # this particular config isn't handled directly by Pandas read_csv, but
            # is an inverse of a Pandas to_csv() option state.
            df.rename_axis(index_names, inplace=True)

        return df

    class _WriteEncodingWrapper:
        # Pandas bug https://github.com/pandas-dev/pandas/issues/23854
        # pandas ignores encoding when writing to io buffers (including files open as 'wb').
        # this results in Pandas trying to write a string into a bytes buffer (and failing)
        # Using this class, we can avoid keeping an additional copy of the data in memory,
        # as otherwise we'd have the DataFrame, the string, and the bytes.
        def __init__(self, bytes_filelike, encoding='utf-8'):
            self.bytes_filelike = bytes_filelike
            self.encoding = encoding

        def __getattr__(self, item):
            return getattr(self.bytes_filelike, item)

        def write(self, string):
            self.bytes_filelike.write(string.encode(self.encoding))

        def writelines(self, lines):
            # function scope import, but this is a bug workaround for pandas.
            from codecs import iterencode
            encoded_lines = iterencode(lines)
            self.bytes_filelike.writelines(encoded_lines)


CSVPandasFormat().register()


class NumpyFormat(BaseFormat):
    name = 'numpy'
    handled_extensions = ['npy', 'npz']

    def handles_type(self, typ):
        # If this is a numpy object, numpy must be loaded.
        if 'numpy' not in sys.modules:
            return False
        import numpy as np
        self.handled_types.add(np.ndarray)
        return super().handles_type(typ)

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        import numpy as np
        buf = io.BytesIO()

        # security -- require an explicit raw_args override to permit pickle usage.
        kwargs = dict(allow_pickle=False)
        if raw_args is not None and 'allow_pickle' not in raw_args:
            raw_args['allow_pickle'] = False

        np.save(buf, obj, **(kwargs if raw_args is None else raw_args))
        return buf.getvalue(), self._update_meta(meta)

    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        import numpy as np

        # security -- require an explicit raw_args override to permit pickle usage.
        kwargs = dict(allow_pickle=False)
        if raw_args is not None and 'allow_pickle' not in raw_args:
            raw_args['allow_pickle'] = False

        buf = io.BytesIO(bytes_obj)
        return np.load(buf, **(kwargs if raw_args is None else raw_args))


NumpyFormat().register()


# noinspection PyPackageRequirements
class ParquetFormat(BaseFormat):
    """Format for Pandas DF <--> Parquet

    Format Opts:
        The following options may be used anywhere format opts are accepted,
        or directly in metadata under `{'format': {'opts': {...: ...}}}`.

        compression(string or dict):  applies during serialization only.
            If a string is given, and string ends in "_columns":
                Use the first part of the string as the compression format for
                each column.
            Otherwise:
                pass-through to the `pyarrow.parquet.write_table()`
    """
    name = 'parquet'
    handled_extensions = ['parquet']
    opts = ('compression')
    defaults = {
        'compression': 'snappy_columns',
    }

    def handles_typ(self, typ):
        # don't load pyarrow or pandas unless we actually have to use them..
        if 'pandas' not in sys.modules:
            return False
        import pandas as pd
        try:
            # intentional unused import -- verify we have pyarrow installed
            import pyarrow as pa
        except ImportError:
            return False
        self.handled_types.add(pd.DataFrame)
        return super().handles_type(typ)

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        import pyarrow as pa
        from pyarrow import parquet

        opts = self.get_opts(meta, format_opts)
        opts_with_defaults = copy.deepcopy(self.defaults)
        opts_with_defaults.update(opts)
        kwargs = {}
        table = pa.Table.from_pandas(obj)

        for name, value in opts_with_defaults.items():
            if name == 'compression':
                if isinstance(value, str) and value.endswith('_columns'):
                    # shorthand for columnar compression on all columns, using prefix value.
                    compression = value.split('_')[0]
                    kwargs['compression'] = {
                        col.name.encode('utf-8'): compression for col in table.columns
                    }
                else:
                    kwargs['compression'] = value

        buf = io.BytesIO()
        parquet.write_table(table, buf, **(raw_args if raw_args is not None else kwargs))

        return buf.getvalue(), self._update_meta(meta, additions=opts_with_defaults)


    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        import pyarrow as pa
        from pyarrow import parquet

        buf = io.BytesIO(bytes_obj)
        table = parquet.read_table(buf)
        try:
            obj = pa.Table.to_pandas(table)
        except AssertionError:
            # Try again to convert the table after removing
            # the possibly buggy Pandas-specific metadata.
            meta = table.schema.metadata.copy()
            meta.pop(b'pandas')
            newtable = table.replace_schema_metadata(meta)
            obj = newtable.to_pandas()
        return obj


ParquetFormat('pyarrow').register()  # compat -- also handle 'pyarrow' target and meta['format']['name'].
ParquetFormat().register()  # latest is preferred
