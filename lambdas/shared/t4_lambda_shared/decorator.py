"""
Decorators for using lambdas in API Gateway
"""

from functools import wraps
import traceback

from jsonschema import Draft4Validator, ValidationError

def api(cors_origins=[]):
    def innerdec(f):
        @wraps(f)
        def wrapper(event, _):
            params = event['queryStringParameters'] or {}
            headers = event['headers'] or {}
            try:
                status, body, response_headers = f(params, headers)
            except Exception as ex:
                traceback.print_exc()
                status = 500
                body = str(ex)
                response_headers = {
                    'Content-Type': 'text/plain'
                }

            origin = headers.get('origin')
            if origin is not None and origin in cors_origins:
                response_headers.update({
                    'access-control-allow-origin': '*',
                    'access-control-allow-methods': 'HEAD,GET,POST',
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
                return 400, str(ex), {'Content-Type': 'text/plain'}

            return f(params, headers)
        return wrapper
    return innerdec
