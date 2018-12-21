import urllib.request

from nbconvert import HTMLExporter
import nbformat
import pandas as pd
from urlib.parse import urlparse

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
    if parse.path.endswith('.parquet'):
        df = pd.read_parquet(url)
        body = df._repr_html_()
    else:
        response = urllib.request.urlopen(url).read().decode()
        notebook = nbformat.reads(response, 4)
        body, resources = html_exporter.from_notebook_node(notebook)

    return {
        "statusCode": 200,
        "body": body,
        "headers": {
            "Content-Type": "text/html"
        }
    }
