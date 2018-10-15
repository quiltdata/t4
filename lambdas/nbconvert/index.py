import urllib.request

from nbconvert import HTMLExporter
import nbformat


html_exporter = HTMLExporter()
html_exporter.template_file = 'full'

def lambda_handler(event, context):
    url = event['queryStringParameters'].get('url')
    if not url:
        return {
            "body": "Missing 'url'",
            "statusCode": 400
        }

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
