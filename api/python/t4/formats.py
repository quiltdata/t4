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
    pass


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
            return (meta_fmt.name if check_only
                    else meta_fmt.serialize(obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts))
        # prefer a format that matches the extension.
        elif ext_fmts:
            for fmt in ext_fmts:
                if fmt in obj_fmts:
                    return (fmt.name if check_only
                            else fmt.serialize(obj, meta=meta, ext=ext, raw_args=raw_args, **format_opts))
        # otherwise, just use the first format that can handle obj.
        if obj_fmts:
            if ext and not check_only:
                print("Notice: No matching serialization formats for extension {!r} with given object."
                      .format(ext))
                print("        Using {!r} format instead.".format(obj_fmts[0].name))
            fmt = obj_fmts[0]
            return (fmt.name if check_only
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
                return meta_fmt.name
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
                return ext_fmt.name
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

    def __init__(self, name=None, handled_extensions=None, handled_types=None):
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

            handled_extensions(list(str)): a list of filename extensions
                that can be deserialized by this format

            handled_types: a list of types that can be serialized to
                (and deserialized from) by this format
        """
        self.name = name if name else getattr(self, 'name', None)
        if not self.name:
            raise TypeError("No `name` attribute has been defined for {!r}".format(type(self).__name__))

        # add user extensions if given
        handled_extensions = [] if handled_extensions is None else handled_extensions
        self.handled_extensions = getattr(self, 'handled_extensions', [])
        self.handled_extensions.extend(ext for ext in handled_extensions if ext not in self.handled_extensions)
        for ext in self.handled_extensions:
            assert ext == ext.lower().strip('. \n')

        # add user types if given
        handled_types = [] if handled_types is None else handled_types
        self.handled_types = getattr(self, 'handled_types', [])
        self.handled_types.extend(typ for typ in handled_types if typ not in self.handled_types)

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
        """Merge `additions` into `meta`.

        `additions` are recursively merged into `meta`.  If a .
        """
        additions = additions if additions else {}
        meta = meta if meta is not None else {}

        format_meta = meta.get('format', {})
        meta['format'] = format_meta   # in case default was used

        if additions:
            format_meta.update(additions)

        format_meta['name'] = self.name

        # compat -- remove once we stop using 'target' in other code.
        meta['target'] = self.name

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
        """
        pass

    def __repr__(self):
        return "<{} {!r}, handling exts {} and types {}>".format(
            type(self).__name__,
            self.name,
            self.handled_extensions,
            list(t.__name__ for t in self.handled_types),
        )

    def _get_opts(self, meta, format_opts, hook):
        if format_opts:
            opts = format_opts
        else:
            meta = meta if meta else {}
            opts = meta.get('format', {}).get('opts', {})

        permitted_opts = self.opts
        result_kwargs = {}
        result_opts = {}
        defaults = getattr(self, 'defaults', {})

        for opt_name in permitted_opts:
            value = opts.get(opt_name, NOT_SET)
            if value is NOT_SET:
                # get the default if present
                value = defaults.get(opt_name, NOT_SET)
                if value is NOT_SET:
                    continue
            else:
                # defaults are excluded from metadata unless specified directly.
                result_opts[opt_name] = value
            arg = hook(opt_name, value)
            if not arg:
                continue
            processed_name, processed_value = arg
            result_kwargs[processed_name] = processed_value

        return result_kwargs, result_opts

    def get_serialization_opts(self, meta, format_opts):
        """Convert opts in `meta` into kwargs for serializer

        For each arg in the `"opts"` dict in the given metadata, this does
        the following:
            1: checks that the option's name is in self.opts
            2: call `self.serialization_opts_hook(name, value)`
            3: skip the arg if `serialization_opts_hook` returns None
            4: otherwise, use the (name, value) pair returned by
               `serialization_opts_hook` as a kwarg for the serializer

        Args:
            meta: metadata to process
            format_opts: If present, use this instead of metadata-derived opts

        Returns:
            (dict of kwargs for serializer, dict of user opts)
        """
        return self._get_opts(meta, format_opts, self.serialization_opts_hook)

    def serialization_opts_hook(self, name, value):
        """Check and potentially modify a specific serializer arg

        If opts are used, this must be overridden, at least as a simple
        pass-through method for the case that kwargs are known to be
        safe and valid for the serializer.

        In other cases, the name or value may be modified to suit the
        serializer, or to make them safe.  Invalid options can be dropped
        by returning a falsey value.

        `name` is a valid/permitted argument name from `self.opts`.
        `value` is an option value retrieved from metadata.

        Returns:
            (name, value) or None -- If (name, value) is returned, it
                will be used as a serializer kwarg.  If None is returned,
                no arg will be added.
        """
        raise NotImplementedError()

    def get_deserialization_opts(self, meta, format_opts):
        """Convert opts in `meta` into kwargs for deserializer

        For each arg in the `"opts"` dict in the given metadata, this does
        the following:
            1: checks that the option's name is in self.opts
            2: call `self.deserialization_opts_hook(name, value)`
            3: skip the arg if `serialization_opts_hook` returns None
            4: otherwise, use the (name, value) pair returned by
               `serialization_opts_hook` as a kwarg for the serializer

        Args:
            meta: metadata to process
            format_opts: If present, use this instead of metadata-derived opts

        Returns:
            (dict of kwargs for serializer, dict of user opts)
        """
        return self._get_opts(meta, format_opts, self.deserialization_opts_hook)

    def deserialization_opts_hook(self, name, value):
        """Check and potentially modify a specific deserializer arg

        If opts are used, this must be overridden, at least as a simple
        pass-through method for the case that kwargs are known to be
        safe and valid for the deserializer.

        In other cases, the name or value may be modified to suit the
        deserializer, or to make them safe.  Invalid options can be dropped
        by returning a falsey value.

        Args:
            name(str): a valid/permitted argument name from `self.opts`.
            value(object): an option value retrieved from metadata.

        Returns:
            (name, value) or None -- If (name, value) is returned, it
                will be used as a serializer kwarg.  If None is returned,
                no arg will be added.
        """
        raise NotImplementedError()


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
        self._update_meta(meta)
        return data

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

        if pd.DataFrame not in self.handled_types:
            self.handled_types.append(pd.DataFrame)

        return super().handles_type(typ)

    def _quoting_opt_to_python(self, name, value):
        if isinstance(value, int):
            return name, value
        elif isinstance(value, str):
            value = value.strip().lower()
            map = {
                'all': csv.QUOTE_ALL,
                'minimal': csv.QUOTE_MINIMAL,
                'none': csv.QUOTE_NONE,
                'nonnumeric': csv.QUOTE_NONNUMERIC
            }
            if value in map:
                return name, map[value]
        print("Unrecognized value for 'quoting' option: {!r}".format(value))
        return None

    def serialization_opts_hook(self, name, value):
        if not isinstance(name, str):
            return
        name = name.strip().lower()

        if name == 'quoting':
            return self._quoting_opt_to_python(name, value)
        if name == 'na_values':
            return 'na_rep', value[0]

        # map names to pandas `df.to_csv() args`
        name_map = {
            'fieldsep': 'sep',
            'linesep': 'line_terminator',
            'use_index': 'index',
            'index_names': 'index_label',
        }
        if name in name_map:
            return name_map[name], value

        # other options are pass-through.
        return name, value

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        kwargs, used_opts = self.get_serialization_opts(meta, format_opts)

        # Use the default delimiter for the given extension, if no fieldsep was specified.
        if ext and 'sep' not in kwargs:
            ext = ext.strip().strip('.').lower()
            ext_map = {'csv': ',', 'tsv': '\t', 'ssv': ';'}
            if ext in ext_map:
                kwargs['sep'] = ext_map[ext]

        # these two args are interdependent, and can't be processed individually by the hook.
        use_header = kwargs.pop('use_header')
        header_names = kwargs.pop('header_names', None)
        if use_header:
            kwargs['header'] = header_names if header_names else True
        else:
            kwargs['header'] = False

        # interdependent args, including pass-through defaults that need processing
        # Does nothing during serialization, but we should check it at least makes sense.
        index_names_are_keys = kwargs.pop('index_names_are_keys')
        if index_names_are_keys:
            if not 'index_names' in used_opts:
                used_opts['index_names'] = list(obj.index.names)
            else:
                if not len(used_opts['index_names']) == len(obj.index.names):
                    raise ValueError("{} entried in `index_names`, but the DataFrame to be serialized has {}"
                                     .format(len(used_opts['index_names']), len(obj.index.names)))

        buf = io.BytesIO()

        # pandas bug workaround -- see _WriteEncodingWraper definition
        encoded_buf = self._WriteEncodingWrapper(buf, encoding=kwargs['encoding'])
        obj.to_csv(encoded_buf, **(raw_args if raw_args is not None else kwargs))

        self._update_meta(meta, additions={'opts': used_opts})

        # return buf.getvalue()
        return buf.getvalue()
        # /workaround

    def deserialization_opts_hook(self, name, value):
        if not isinstance(name, str):
            return
        name = name.strip().lower()

        if name == 'quoting':
            return self._quoting_opt_to_python(name, value)

        # map names to pandas `df.to_csv() args`
        name_map = {
            'fieldsep': 'sep',
            'linesep': 'lineterminator',
        }
        if name in name_map:
            return name_map[name], value

        # other options are pass-through.
        return name, value

    def deserialize(self, bytes_obj, meta=None, ext=None, raw_args=None, **format_opts):
        import pandas as pd

        kwargs, used_opts = self.get_deserialization_opts(meta, format_opts)

        # Use the default delimiter for the given extension, if no fieldsep was specified.
        if ext and 'sep' not in kwargs:
            ext = ext.strip().strip('.').lower()
            ext_map = {'csv': ',', 'tsv': '\t', 'ssv': ';'}
            if ext in ext_map:
                kwargs['sep'] = ext_map[ext]

        # use_header, header_names, and index_names_are_keys aren't valid serializer kwargs,
        # they're pass-through opts that need special handling do act like serialize() would
        # expect.
        header_names = kwargs.pop('header_names', None)
        index_names = kwargs.pop('index_names', None)
        use_header = kwargs.pop('use_header')  # opt should be present from defaults.
        use_index = kwargs.pop('use_index')   # opt should be present from defaults.
        index_names_are_keys = kwargs.pop('index_names_are_keys', False)

        if use_header:
            kwargs['header'] = 0
            if header_names:
                kwargs['names'] = header_names
        else:
            kwargs['header'] = None
            kwargs['names'] = header_names

        if use_index:
            if index_names:
                if index_names_are_keys:
                    kwargs['index_col'] = index_names
                else:
                    kwargs['index_col'] = list(range(len(index_names)))
            else:
                kwargs['index_col'] = [0]
        else:
            kwargs['index_col'] = False

        df = pd.read_csv(io.BytesIO(bytes_obj), **raw_args if raw_args else kwargs)

        if index_names and not index_names_are_keys:
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
        if np.ndarray not in self.handled_types:
            self.handled_types.append(np.ndarray)
        return super().handles_type(typ)

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        import numpy as np
        buf = io.BytesIO()

        # security -- require an explicit raw_args override to permit pickle usage.
        kwargs = dict(allow_pickle=False)
        if raw_args is not None and 'allow_pickle' not in raw_args:
            raw_args['allow_pickle'] = False

        np.save(buf, obj, **(kwargs if raw_args is None else raw_args))
        self._update_meta(meta)
        return buf.getvalue()

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

    def serialization_opts_hook(self, name, value):
        if name in self.opts:
            return name, value

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
        if pd.DataFrame not in self.handled_types:
            self.handled_types.append(pd.DataFrame)
        return super().handles_type(typ)

    def serialize(self, obj, meta=None, ext=None, raw_args=None, **format_opts):
        import pyarrow as pa
        from pyarrow import parquet
        kwargs, used_opts = self.get_deserialization_opts(meta, format_opts)
        
        buf = io.BytesIO()
        table = pa.Table.from_pandas(obj)

        compression = kwargs.get('compression')
        if isinstance(compression, str) and compression.endswith('_columns'):
            compression = compression.rsplit('_')[0]
            kwargs['compression'] = {col.name.encode('utf-8'): compression for col in table.columns} 

        parquet.write_table(table, buf, **(raw_args if raw_args is not None else kwargs))
        self._update_meta(meta, additions=used_opts)
        return buf.getvalue()


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
