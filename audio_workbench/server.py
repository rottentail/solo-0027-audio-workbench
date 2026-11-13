import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .service import execute

MAX_BODY = 8 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, result):
        payload = json.dumps(result, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        try:
            parts = self.path.strip('/').split('/')
            if len(parts) == 2 and parts[0] == 'jobs':
                result = self.server.jobs.get(parts[1])
            elif len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'result':
                result = self.server.jobs.result(parts[1])
            else:
                raise LookupError('unknown endpoint')
            self.respond(200, result)
        except LookupError as exc:
            self.respond(404, {'error': str(exc)})
        except ValueError as exc:
            self.respond(400, {'error': str(exc)})

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
            body = json.loads(data)
            parts = self.path.strip('/').split('/')
            if self.path == '/jobs':
                result, status = self.server.jobs.submit(body), 202
            elif len(parts) == 3 and parts[0] == 'jobs' and parts[2] == 'cancel':
                result, status = self.server.jobs.cancel(parts[1]), 200
            else:
                result, status = execute(self.path, body), 200
        except LookupError as exc:
            status, result = 404, {'error': str(exc)}
        except (ValueError, UnicodeDecodeError) as exc:
            status, result = 400, {'error': str(exc)}
        self.respond(status, result)


def main():
    parser = argparse.ArgumentParser(description='PCM audio processing HTTP service')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--data-dir', default=os.environ.get('AUDIO_WORKBENCH_DATA', './media-data'))
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    from .jobs import JobManager
    jobs = JobManager(args.data_dir, args.workers)
    try:
        with ThreadingHTTPServer((args.host, args.port), Handler) as server:
            server.jobs = jobs
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    finally:
        jobs.close()


if __name__ == '__main__':
    main()
