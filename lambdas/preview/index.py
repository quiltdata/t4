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
    """
    url = params['url']
    input_type = params.get('input')

    resp = requests.get(url)
    if resp.ok:
        with NamedTemporaryFile() as file_:
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
    (in that order, up to MAX_LINES)

    Args:
        file_ - file-like
    """
    meta = []
    header = []
    data = []
    size = 0

    with open(file_.name, 'rb') as vcf:
        for index, line in enumerate(vcf, start=1):
            # don't escape quotes
            line = line.rstrip().decode()
            size += len(line)
            if line.startswith('##'):
                meta.append(line)
            elif line.startswith('#'):
                header.append(line)
            else:
                data.append(line)
            # stop if we're over the max
            if index >= MAX_LINES or size > MAX_BYTES:
                break

    info = {
        'data': {
            'meta': meta,
            'header': header,
            'data': data,
        }
    }

    return '', info

def extract_txt(file_):
    """
    Display first and last few lines of a potentially large file.

    Args:
        file_ - file-like object
    """
    size = 0
    ellipsis = False
    head = []
    with open(file_.name, 'rb') as txt:
        for index, line in enumerate(txt, start=1):
            line = line.rstrip().decode()
            size += len(line)
            # this is a heuristic; can fail to return shorter tail lines
            # if head lines are uncharacteristically long
            # we're guarding against, for example, huge single-line JSON files
            if index <= MAX_LINES and size < MAX_BYTES:
                head.append(line)
            if size > MAX_BYTES:
                break
            if index > MAX_LINES:
                ellipsis = True
                break
    tail = []
    if ellipsis: # in this case we need a tail
        headlen = int(MAX_LINES/2) # pylint: disable=old-division
        taillen = MAX_LINES - headlen
        # cut head
        head = head[:headlen]
        # grow tail
        with open(file_.name, 'rb') as txt:
            count = 0
            txt.seek(0, os.SEEK_END) # the very end
            while count < taillen:
                txt.seek(-2, os.SEEK_CUR)
                if txt.read(1) == b'\n':
                    count +=1 

            for _ in range(taillen):
                line = txt.readline().rstrip().decode()
                size += len(line)
                if size < MAX_BYTES:
                    tail.append(line)

    info = {
        'data': {
            'head': head,
            'tail': tail
        }
    }
    return '', info
