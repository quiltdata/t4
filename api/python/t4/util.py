import re
from collections import Mapping, Sequence, Set, OrderedDict
import datetime
import json
import os
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import url2pathname

# backports
from six.moves import urllib
try:
    import pathlib2 as pathlib
except ImportError:
    import pathlib

# Third-Party
import ruamel.yaml
from appdirs import user_data_dir


APP_NAME = "T4"
APP_AUTHOR = "QuiltData"
BASE_DIR = user_data_dir(APP_NAME, APP_AUTHOR)
BASE_PATH = pathlib.Path(BASE_DIR)
CONFIG_PATH = BASE_PATH / 'config.yml'

PACKAGE_NAME_FORMAT = r"[\w-]+/[\w-]+$"

## CONFIG_TEMPLATE
# Must contain every permitted config key, as well as their default values (which can be 'null'/None).
# Comments are retained and added to local config, unless overridden by autoconfig via `api.config(<url>)`
CONFIG_TEMPLATE = """
# Helium configuration file

# navigator_url: <url string, default: null>
#
# Used for autoconfiguration
# navigator_url: https://example.com
navigator_url:

# elastic_search_url: <url string, default: null>
#
# Used to satisfy search queries
# elastic_search_url: https://example.com/es
elastic_search_url:
"""


class QuiltException(Exception):
    def __init__(self, message, **kwargs):
        # We use NewError("Prefix: " + str(error)) a lot.
        # To be consistent across Python 2.7 and 3.x:
        # 1) This `super` call must exist, or 2.7 will have no text for str(error)
        # 2) This `super` call must have only one argument (the message) or str(error) will be a repr of args
        super(QuiltException, self).__init__(message)
        self.message = message
        for k, v in kwargs.items():
            setattr(self, k, v)


def fix_url(url):
    """Convert non-URL paths to file:// URLs"""
    # If it has a scheme, we assume it's a URL.
    # On Windows, we ignore schemes that look like drive letters, e.g. C:/users/foo
    if not url:
        raise ValueError("Empty URL")

    url = str(url)

    parsed = urlparse(url)
    if parsed.scheme and not os.path.splitdrive(url)[0]:
        return url

    # `resolve()` _tries_ to make the URI absolute - but doesn't guarantee anything.
    # In particular, on Windows, non-existent files won't be resolved.
    # `absolute()` makes the URI absolute, though it can still contain '..'
    fixed_url = pathlib.Path(url).resolve().absolute().as_uri()

    # pathlib likes to remove trailing slashes, so add it back if needed.
    if url[-1:] in (os.sep, os.altsep) and not fixed_url.endswith('/'):
        fixed_url += '/'

    return fixed_url


def parse_s3_url(s3_url):
    """
    Takes in the result of urlparse, and returns a tuple (bucket, path, version_id)
    """
    if s3_url.scheme != 's3' or not s3_url.netloc or (s3_url.path and not s3_url.path.startswith('/')):
        raise ValueError("Malformed S3 URI")
    bucket = s3_url.netloc
    path = unquote(s3_url.path)[1:]
    # Parse the version ID the way the Java SDK does:
    # https://github.com/aws/aws-sdk-java/blob/master/aws-java-sdk-s3/src/main/java/com/amazonaws/services/s3/AmazonS3URI.java#L192
    query = parse_qs(s3_url.query)
    version_id = query.pop('versionId', [None])[0]
    if query:
        raise ValueError("Unexpected S3 query string: %r" % s3_url.query)
    return bucket, path, version_id


def parse_file_url(file_url):
    if file_url.scheme != 'file':
        raise ValueError("Invalid file URI")
    path = url2pathname(file_url.path)
    if file_url.netloc not in ('', 'localhost'):
        # Windows file share
        # TODO: Can't do anything useful on non-Windows... Return an error?
        path = '\\\\%s%s' % (file_url.netloc, path)
    return path


def read_yaml(yaml_stream):
    yaml = ruamel.yaml.YAML()
    try:
        return yaml.load(yaml_stream)
    except ruamel.yaml.parser.ParserError as error:
        raise QuiltException(str(error), original_error=error)


# If we won't be using YAML for anything but config.yml, we can drop keep_backup and assume True.
def write_yaml(data, yaml_path, keep_backup=False):
    """Write `data` to `yaml_path`

    :param data: Any yaml-serializable data
    :param yaml_path: Destination. Can be a string or pathlib path.
    :param keep_backup: If set, a timestamped backup will be kept in the same dir.
    """
    yaml = ruamel.yaml.YAML()
    path = pathlib.Path(yaml_path)
    now = str(datetime.datetime.now())

    # XXX unicode colon for Windows/NTFS -- looks prettier, but could be confusing. We could use '_' instead.
    if os.name == 'nt':
        now = now.replace(':', '\ua789')

    backup_path = path.with_name(path.name + '.backup.' + now)

    try:
        if path.exists():
            path.rename(backup_path)
        if not path.parent.exists():
            path.parent.mkdir(parents=True)
        with path.open('w') as config_file:
            yaml.dump(data, config_file)
    except Exception:     #! intentionally wide catch -- reraised immediately.
        if backup_path.exists():
            if path.exists():
                path.unlink()
            backup_path.rename(path)
        raise

    if backup_path.exists() and not keep_backup:
        backup_path.unlink()


def yaml_has_comments(parsed):
    """Determine if parsed YAML data has comments.

    Any object can be given, but only objects based on `ruamel.yaml`'s
    `CommentedBase` class can be True.

    :returns: True if object has retained comments, False otherwise
    """
    # Is this even a parse result object that stores comments?
    if not isinstance(parsed, ruamel.yaml.comments.CommentedBase):
        return False

    # Are there comments on this object?
    if parsed.ca.items or parsed.ca.comment or parsed.ca.end:
        return True

    # Is this a container that might have values with comments?
    values = ()
    if isinstance(parsed, (Sequence, Set)):
        values = parsed
    if isinstance(parsed, Mapping):
        values = parsed.values()
    # If so, do any of them have comments?
    for value in values:
        if yaml_has_comments(value):
            return True
    # no comments found.
    return False


def validate_url(url):
    """A URL must have scheme and host, at minimum."""
    parsed_url = urllib.parse.urlparse(url)

    # require scheme and host at minimum, like config_path'http://foo'
    if not all((parsed_url.scheme, parsed_url.netloc)):
        raise QuiltException("Invalid URL -- Requires at least scheme and host: {}".format(url))
    try:
        parsed_url.port
    except ValueError:
        raise QuiltException("Invalid URL -- Port must be a number: {}".format(url))


# Although displaying the config may seem not to warrant a class, it's pretty important
# for good UX. A lot of points were considered in making this -- retaining order,
# user's usage in an interpreted environment like Jupyter, and keeping the displayed
# information concise.  Given the limitations of the other options, making a class with
# custom repr panned out to be the best (and shortest) option.
class HeliumConfig(OrderedDict):
    def __init__(self, filepath, *args, **kwargs):
        self.filepath = pathlib.Path(filepath)
        super(HeliumConfig, self).__init__(*args, **kwargs)

    def __repr__(self):
        return "<{} at {!r} {}>".format(type(self).__name__, str(self.filepath), json.dumps(self, indent=4))


def validate_package_name(name):
    """ Verify that a package name is two alphanumerics strings separated by a slash."""
    if not re.match(PACKAGE_NAME_FORMAT, name):
        raise QuiltException("Invalid package name, must contain exactly one /.")