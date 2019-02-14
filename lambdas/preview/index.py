"""
Preview file types in S3 by returning preview HTML and other metadata from
a lambda function.
"""
from functools import wraps
import json
import os
from tempfile import NamedTemporaryFile
import traceback

from jsonschema import Draft4Validator, ValidationError
from nbconvert import HTMLExporter
import nbformat
import pyarrow.parquet as pq
import requests


# TODO(dima): Move these into a library?

def api(cors_origins=[]):
    def innerdec(f):
        @wraps(f)
        def wrapper(event, _):
            params = event['queryStringParameters'] or {}
            headers = event['headers'] or {}
            try:
                status, body, response_headers = f(params, headers)
            except Exception:
                traceback.print_exc()
                status = 500
                body = 'Internal Server Error'
                response_headers = {
                    'Content-Type': 'text/plain'
                }

            origin = headers.get('origin')
            if origin is not None and origin in cors_origins:
                response_headers.update({
                    'access-control-allow-origin': '*',
                    'access-control-allow-methods': 'GET',
                    'access-control-allow-headers': '*',
                    'access-control-max-age': 86400
                })

            return {
                "statusCode": status,
                "body": body,
                "headers": response_headers
            }
        return wrapper
    return innerdec


def validate(schema):
    Draft4Validator.check_schema(schema)
    validator = Draft4Validator(schema)

    def innerdec(f):
        @wraps(f)
        def wrapper(params, headers):
            try:
                validator.validate(params)
            except ValidationError as ex:
                return 400, str(ex), {}

            return f(params, headers)
        return wrapper
    return innerdec


ALLOWED_ORIGINS = [
    'http://localhost:3000',
    os.environ.get('WEB_ORIGIN')
]

SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string'
        },
        'input': {
            'enum': ['ipynb', 'parquet']
        }
    },
    'required': ['url', 'input'],
    'additionalProperties': False
}

@api(cors_origins=ALLOWED_ORIGINS)
@validate(SCHEMA)
def lambda_handler(params, _):
    """
    dynamically handle preview requests for bytes in S3

    caller must specify input_type (since there may be no file extension)
    """
    url = params['url']
    input_type = params.get('input')

    resp = requests.get(url)
    if resp.ok:
        with NamedTemporaryFile() as file_:
            for chunk in resp.iter_content(chunk_size=1024):
                file_.write(chunk)
            file_.seek(0)
            # init variables used across cases so ret_val never barfs on missing data
            html = ''
            info = {}
            if input_type == 'ipynb':
                html_exporter = HTMLExporter()
                html_exporter.template_file = 'basic'

                notebook = nbformat.read(file_, 4)
                html, _ = html_exporter.from_notebook_node(notebook)
            elif input_type == 'parquet':
                # TODO: generalize to datasets, multipart files
                # As written, only works for single files, and metadata
                # is slanted towards the first row_group
                meta = pq.read_metadata(file_)
                info['created_by'] = meta.created_by
                info['format_version'] = meta.format_version
                info['metadata'] = {
                    # seems silly but sets up a simple json.dumps(info) below
                    k.decode():json.loads(meta.metadata[k])
                    for k in meta.metadata
                }
                info['num_row_groups'] = meta.num_row_groups
                info['schema'] = {
                    name: {
                        'logical_type': meta.schema.column(i).logical_type,
                        'max_definition_level': meta.schema.column(i).max_definition_level,
                        'max_repetition_level': meta.schema.column(i).max_repetition_level,
                        'path': meta.schema.column(i).path,
                        'physical_type': meta.schema.column(i).physical_type,
                    }
                    for i, name in enumerate(meta.schema.names)
                }
                info['serialized_size'] = meta.serialized_size
                info['shape'] = [meta.num_rows, meta.num_columns]

                file_.seek(0)
                # TODO: make this faster with n_threads > 1?
                row_group = pq.ParquetFile(file_).read_row_group(0)
                # convert to str since FileMetaData is not JSON.dumps'able (below)
                html = row_group.to_pandas()._repr_html_() # pylint: disable=protected-access
            else:
                assert False

        ret_val = {
            'info': info,
            'html': html,
        }

    else:
        ret_val = {
            'error': resp.reason
        }

    response_headers = {
        "Content-Type": 'application/json'
    }

    return 200, json.dumps(ret_val), response_headers
