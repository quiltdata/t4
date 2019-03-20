#!/usr/bin/env python3

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import sys
from urllib.parse import urlparse, parse_qsl, unquote

from index import lambda_handler


PORT = 8080
LAMBDA_PATH = '/lambda'

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = unquote(parsed_url.path)

        if path == LAMBDA_PATH:
            query = dict(parse_qsl(parsed_url.query))
            headers = self.headers

            args = {
                'queryStringParameters': query or None,
                'headers': headers or None
            }

            result = lambda_handler(args, None)

            code = result['statusCode']
            headers = result['headers']
            body = result['body'].encode()

            headers['Content-Length'] = str(len(body))

            self.send_response(code)
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')


def main(argv):
    if len(argv) != 1:
        print('Usage: %s', file=sys.stderr)
        return 1

    server_address = ('127.0.0.1', PORT)
    print("Running on http://%s:%d%s" % (server_address[0], server_address[1], LAMBDA_PATH))
    server = HTTPServer(server_address, Handler)
    server.serve_forever()


if __name__ == '__main__':
    sys.exit(main(sys.argv))
