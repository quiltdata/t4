"""
Preview file types in S3 by returning preview HTML and other metadata from
a lambda function.
"""
import json
import os
from tempfile import NamedTemporaryFile

from jsonschema import Draft4Validator, ValidationError
from nbconvert import HTMLExporter
import nbformat
import pyarrow.parquet as pq
import requests


ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:3000/',
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

Draft4Validator.check_schema(SCHEMA)
VALIDATOR = Draft4Validator(SCHEMA)

def lambda_handler(event, _):
    """
    dynamically handle preview requests for bytes in S3

    caller must specify input_type (since there may be no file extension)
    """
    # this weird-looking code is correct since event['queryStringParameters']
    # will return a None if no query params
    params = event['queryStringParameters'] or {}
    headers = event['headers'] or {}

    try:
        VALIDATOR.validate(params)
    except ValidationError as ex:
        return {
            "body": str(ex),
            "statusCode": 400
        }

    url = params['url']
    input_type = params.get('input')

    resp = requests.get(url)
    if resp.ok:
        with NamedTemporaryFile() as fd:
            for chunk in resp.iter_content(chunk_size=1024):
                fd.write(chunk)
            fd.seek(0)
            # init variables used across cases so ret_val never barfs on missing data
            html = ''
            info = {}
            if input_type == 'ipynb':
                html_exporter = HTMLExporter()
                html_exporter.template_file = 'basic'

                notebook = nbformat.read(fd, 4)
                html, _ = html_exporter.from_notebook_node(notebook)
            elif input_type == 'parquet':
                # TODO: generalize to datasets, multipart files
                # As written, only works for single files, and metadata
                # is slanted towards the first row_group
                meta = pq.read_metadata(fd)
                info['created_by'] = meta.created_by
                info['format_version'] = meta.format_version
                info['metadata'] = {
                    # seems silly but sets up a simple json.dumps(info) below
                    k.decode():json.loads(meta.metadata[k])
                    for k in meta.metadata
                }
                info['num_row_groups'] = meta.num_row_groups
                info['schema'] = {
                    meta.schema.names[i]: {
                        'logical_type': meta.schema.column(i).logical_type,
                        'max_definition_level': meta.schema.column(i).max_definition_level,
                        'max_repetition_level': meta.schema.column(i).max_repetition_level,
                        'path': meta.schema.column(i).path,
                        'physical_type': meta.schema.column(i).physical_type,
                    }
                    for i in range(len(meta.schema.names))
                }
                info['serialized_size'] = meta.serialized_size
                info['shape'] = [meta.num_rows, meta.num_columns]

                fd.seek(0)
                # TODO: make this faster with n_threads > 1?
                row_group = pq.ParquetFile(fd).read_row_group(0)
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
    if headers.get('origin') in ALLOWED_ORIGINS:
        response_headers.update({
            'access-control-allow-origin': '*',
            'access-control-allow-methods': 'GET',
            'access-control-allow-headers': '*',
            'access-control-max-age': 86400
        })

    return {
        "statusCode": 200,
        "body": json.dumps(ret_val),
        "headers": response_headers
    }
