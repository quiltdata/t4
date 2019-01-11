from enum import Enum
import json
import os
import urllib.request

from jsonschema import Draft4Validator, ValidationError
from nbconvert import HTMLExporter
import nbformat
import pandas as pd
from urllib.parse import urlparse, unquote

WEB_ORIGIN = os.environ['WEB_ORIGIN']


SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string'
        },
        'output': {
            'enum': ['html', 'json']
        },
        'input': {
            'enum': ['ipynb', 'parquet']
        },
        'nbconvert_template': {
            'enum': ['full', 'basic']
        }
    },
    'required': ['url'],
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

    # TODO(dima): Make it required.
    if input_type is None:
        parsed_url = urlparse(url)
        path = unquote(parsed_url.path)
        if path.endswith('.parquet'):
            input_type = 'parquet'
        else:
            input_type = 'ipynb'


    if input_type == 'ipynb':
        html_exporter = HTMLExporter()
        html_exporter.template_file = params.get('nbconvert_template', 'full')

        response = urllib.request.urlopen(url).read().decode()
        notebook = nbformat.reads(response, 4)
        result, _ = html_exporter.from_notebook_node(notebook)
    elif input_type == 'parquet':
        df = pd.read_parquet(url)
        result = df._repr_html_()
    else:
        assert False

    output = params.get('output', 'html')

    if output == 'json':
        body = json.dumps({
            'body': result
        })
        content_type = 'application/json'
    elif output == 'html':
        body = result
        content_type = 'text/html'
    else:
        assert False

    response_headers = {
        "Content-Type": content_type
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
        "body": body,
        "headers": response_headers
    }
