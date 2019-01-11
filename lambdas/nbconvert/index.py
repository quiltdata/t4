"""
Return preview for given file type.
Currently handles:
* .parquet
* Ipynb
"""
import io
import json

from nbconvert import HTMLExporter
import nbformat
import pandas as pd
import pyarrow as pa
import urllib.request
from urllib.parse import urlparse

html_exporter = HTMLExporter()
html_exporter.template_file = 'full'

def lambda_handler(event, context):
    url = event['queryStringParameters'].get('url')
    if not url:
        return {
            "body": "Missing 'url'",
            "statusCode": 400
        }

    parse = urlparse(url)
    response = urllib.request.urlopen(url) 
    filelike = io.BytesIO(response.read())

    if parse.path.lower().endswith('.parquet'):
        # TODO: make this memory efficient for large files (use slicing?)
        df = pd.read_parquet(url)
        filelike.seek(0) # reset so pyarrow can read again
        meta = pa.read_metadata(filelike)
        moremeta = {k.decode():json.loads(meta.metadata[k]) for k in meta.metadata}
        body = json.dumps({
            'metadata': moremeta, 
            'summary': str(meta),
            'table_html': df._repr_html_(),
        })
    elif parse.path.lower().endswith('.ipynb'):
        notebook = nbformat.reads(filelike.read.decode(), 4)
        body, resources = html_exporter.from_notebook_node(notebook)

    return {
        "statusCode": 200,
        "body": body,
        "headers": {
            "Content-Type": "text/html"
        }
    }
