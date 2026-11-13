import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .service import execute

MAX_BODY = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            if self.headers.get('Transfer-Encoding'):
                raise ValueError('transfer encoding is not supported')
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= MAX_BODY:
                raise ValueError('invalid request size')
            data = self.rfile.read(length)
            if len(data) != length:
                raise ValueError('incomplete request')
            result = execute(self.path, json.loads(data))
            status = 200
        except LookupError as exc:
            status, result = 404, {'error': str(exc)}
        except (ValueError, UnicodeDecodeError) as exc:
            status, result = 400, {'error': str(exc)}
        payload = json.dumps(result, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description='PCM audio processing HTTP service')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
