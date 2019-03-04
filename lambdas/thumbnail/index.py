"""
Generate thumbnails for images in S3.
"""
import base64
from io import BytesIO
import json
import os

from PIL import Image
import requests

from t4_lambda_shared.decorator import api, validate


# Eventually we'll want to precompute/cache thumbnails, so we won't be able to support
# arbitrary sizes. Might as well copy Dropbox' API:
# https://www.dropbox.com/developers/documentation/http/documentation#files-get_thumbnail
SUPPORTED_SIZES = [
    (32, 32),
    (64, 64),
    (128, 128),
    (256, 256),
    (480, 320),
    (640, 480),
    (960, 640),
    (1024, 768),
    (2048, 1536)
]
# Map URL parameters to actual sizes, e.g. 'w128h128' -> (128, 128)
# TODO(dima): Is this a good idea? Don't know why Dropbox does it that way.
SIZE_PARAMETER_MAP = {f'w{w}h{h}': (w, h) for w, h in SUPPORTED_SIZES}

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
        'size': {
            'enum': list(SIZE_PARAMETER_MAP)
        }
    },
    'required': ['url', 'size'],
    'additionalProperties': False
}

@api(cors_origins=ALLOWED_ORIGINS)
@validate(SCHEMA)
def lambda_handler(params, _):
    """
    Generate thumbnails for images in S3
    """
    url = params['url']
    size = SIZE_PARAMETER_MAP[params['size']]

    resp = requests.get(url)
    if resp.ok:
        image_bytes = BytesIO(resp.content)
        with Image.open(image_bytes) as image:
            orig_format = image.format
            orig_size = image.size
            image.thumbnail(size)
            thumbnail_size = image.size
            thumbnail_bytes = BytesIO()
            image.save(thumbnail_bytes, image.format)

        encoded = base64.b64encode(thumbnail_bytes.getvalue()).decode()

        ret_val = {
            'info': {
                'original_format': orig_format,
                'original_size': orig_size,
                'thumbnail_format': orig_format,
                'thumbnail_size': thumbnail_size,
            },
            'thumbnail': encoded,
        }
    else:
        ret_val = {
            'error': resp.reason
        }

    response_headers = {
        "Content-Type": 'application/json'
    }

    return 200, json.dumps(ret_val), response_headers
