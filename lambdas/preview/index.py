"""
Preview file types in S3 by returning preview HTML and other metadata from
a lambda function.
"""
import json
import os
from tempfile import NamedTemporaryFile

from nbconvert import HTMLExporter
import nbformat
import pyarrow.parquet as pq
import requests

from t4_lambda_shared.decorator import api, validate
from t4_lambda_shared.utils import get_default_origins, make_json_response

MAX_BYTES = 1_000_000 # must be positive int
MAX_LINES = 500 # must be positive int

SCHEMA = {
    'type': 'object',
    'properties': {
        'url': {
            'type': 'string'
        },
        'input': {
            'enum': ['ipynb', 'parquet', 'txt', 'vcf']
        }
    },
    'required': ['url', 'input'],
    'additionalProperties': False
}

@api(cors_origins=get_default_origins())
@validate(SCHEMA)
def lambda_handler(params, _):
    """
    dynamically handle preview requests for bytes in S3
    caller must specify input_type (since there may be no file extension)

    Returns:
        JSON response
    """
    url = params['url']
    input_type = params.get('input')

    resp = requests.get(url)
    if resp.ok:
        with NamedTemporaryFile(mode='r+b') as file_:
            for chunk in resp.iter_content(chunk_size=1024):
                file_.write(chunk)
            file_.seek(0)

            if input_type == 'ipynb':
                html, info = extract_ipynb(file_)
            elif input_type == 'parquet':
                html, info = extract_parquet(file_)
            elif input_type == 'vcf':
                html, info = extract_vcf(file_)
            elif input_type == 'txt':
                html, info = extract_txt(file_)
            else:
                assert False

        assert isinstance(html, str), 'expected html parameter as string'
        assert isinstance(info, dict), 'expected info metadata to be a dict'

        ret_val = {
            'info': info,
            'html': html,
        }

    else:
        ret_val = {
            'error': resp.reason
        }

    return make_json_response(200, ret_val)

def extract_ipynb(file_):
    """
    parse and extract ipynb files

    Args:
        file_ - named temporary file

    Returns:
        html - html version of notebook
        info - unmodified (is also passed in)
    """
    html_exporter = HTMLExporter()
    html_exporter.template_file = 'basic'

    notebook = nbformat.read(file_, 4)
    html, _ = html_exporter.from_notebook_node(notebook)

    return html, {}

def extract_parquet(file_):
    """
    parse and extract key metadata from parquet files

    Args:
        file_ - named temporary file

    Returns:
        dict
            html - html summary of main contents (if applicable)
            info - metdata for user consumption
    """
    # TODO: generalize to datasets, multipart files
    # As written, only works for single files, and metadata
    # is slanted towards the first row_group
    meta = pq.read_metadata(file_)

    info = {}
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

    return html, info

def extract_vcf(file_):
    """
    Pull summary info from VCF: meta-information, header line, and data lines
    (in that order, up to MAX_LINES). Skips empty lines.

    Args:
        file_ - file-like object
    
    Returns:
        dict
    """
    meta = []
    header = []
    data = []
    size = 0
    for line in file_:
        line = _truncate(line.rstrip(), MAX_BYTES - size)
        if line.startswith(b'##'):
            meta.append(line)
        elif line.startswith(b'#'):
            header.append(line)
        elif line:
            data.append(line)
        size += len(line)
        total_lines = len(meta) + len(header) + len(data)
        if total_lines >= MAX_LINES or size >= MAX_BYTES:
            break

    info = {
        'data': {
            # ignore b/c we might snap a multi-byte unicode character in two
            'meta': [s.decode('utf-8', 'ignore') for s in meta],
            'header': [s.decode('utf-8', 'ignore') for s in header],
            'data': [s.decode('utf-8', 'ignore') for s in data]
        }
    }

    return '', info

def extract_txt(file_):
    """
    Display first and last few lines of a potentially large file.
    Because we process files in binary mode, we risk breaking some unicode
    characters mid-word. Skips empty lines.

    Args:
        file_ - file-like object
    Returns:
        dict - head and tail. tail may be empty. returns at most MAX_LINES
        lines that occupy a total of MAX_BYTES bytes.
    """
    size = 0
    head = []
    tail = []
    for index, line in enumerate(file_, start=1):
        line = _truncate(line.rstrip(), MAX_BYTES - size)
        size += len(line)
        if line and len(head) < MAX_LINES:
            head.append(line)
        # if the file is longer than MAX_LINES, we need a tail
        if index > MAX_LINES:
            headmax = MAX_LINES//2
            tailmax = MAX_LINES - headmax
            # cut the head back to make room for the tail
            head = head[:headmax]
            # correct the size for the lines we just dropped
            size = sum([len(s) for s in head])
            file_size = os.stat(file_.name).st_size
            # avoid rewinding past start of file
            remaining = min(MAX_BYTES - size, file_size)
            # go to the earliest available byte
            file_.seek(-remaining, os.SEEK_END)
            # remaining lines, less empty lines
            tail = [l for l in file_.read().split(b'\n') if l]
            # chop tails with lots of lines, OR, if we only have a few lines,
            # throw away the very first line, because it might not be complete
            tail = tail[-tailmax:] if len(tail) > tailmax else tail[1:]
            break

    info = {
        'data': {
            'head': [s.decode('utf-8', 'ignore') for s in head],
            'tail': [s.decode('utf-8', 'ignore') for s in tail]
        }
    }

    return '', info

def _truncate(line, stop):
    """chop string, if needed, to fit in remaining characters
    Args:
        line - string to truncate
        stop - max allowable characters
    Returns:
        string
    """
    return line[:max(0, stop)]
