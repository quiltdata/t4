import json
import os
from tempfile import NamedTemporaryFile

from jsonschema import Draft4Validator, ValidationError
from nbconvert import HTMLExporter
import nbformat
import pandas as pd
import requests

WEB_ORIGIN = os.environ['WEB_ORIGIN']


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


def lambda_handler(event, context):
    params = event['queryStringParameters'] or {}
    headers = event['headers'] or {}

    try:
        VALIDATOR.validate(params)
    except ValidationError as ex:
        return {
            "body": ex.message,
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

            if input_type == 'ipynb':
                html_exporter = HTMLExporter()
                html_exporter.template_file = 'basic'

                notebook = nbformat.read(fd, 4)
                html, _ = html_exporter.from_notebook_node(notebook)
            elif input_type == 'parquet':
                df = pd.read_parquet(fd.name)
                html = df._repr_html_()
            else:
                assert False

        ret_val = {
            'html': html
        }
    else:
        ret_val = {
            'error': resp.reason
        }

    response_headers = {
        "Content-Type": 'application/json'
    }
    if headers.get('origin') == WEB_ORIGIN:
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
