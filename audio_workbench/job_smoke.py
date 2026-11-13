"""Exercise media jobs through HTTP with a generated audiovisual source."""
import base64
import json
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import imageio_ffmpeg
from .jobs import JobManager
from .server import Handler


def main():
    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / 'sample.mp4'
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        subprocess.run([ffmpeg, '-loglevel', 'error', '-f', 'lavfi', '-i', 'testsrc=size=160x120:rate=10',
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=8000', '-t', '1',
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-y', str(source)],
                       check=True, timeout=30)
        manager = JobManager(Path(tmp) / 'data', workers=2)
        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            server.jobs = manager
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def call(path, body=None):
                data = None if body is None else json.dumps(body).encode()
                request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}{path}', data,
                                                 {'Content-Type': 'application/json'})
                try:
                    with urllib.request.urlopen(request, timeout=5) as response:
                        return response.status, json.load(response)
                except urllib.error.HTTPError as exc:
                    return exc.code, json.load(exc)
            def finish(job_id):
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    job = call('/jobs/' + job_id)[1]
                    if job['status'] in ('succeeded', 'failed', 'cancelled'):
                        return job
                    time.sleep(.05)
                raise RuntimeError('job timed out')
            try:
                encoded = base64.b64encode(source.read_bytes()).decode()
                ids = []
                for preset in ('mp4', 'audio'):
                    status, job = call('/jobs', {'source': encoded, 'preset': preset, 'start': .1, 'duration': .5})
                    assert status == 202
                    ids.append(job['id'])
                for job_id in ids:
                    job = finish(job_id)
                    assert job['status'] == 'succeeded', job
                    status, result = call('/jobs/' + job_id + '/result')
                    assert status == 200 and result['sha256'] == job['sha256']
                    rendered = Path(tmp) / (job_id + '.media')
                    rendered.write_bytes(base64.b64decode(result['audio_video']))
                    subprocess.run([ffmpeg, '-v', 'error', '-i', str(rendered), '-f', 'null', '-'],
                                   check=True, timeout=30)
                status, job = call('/jobs', {'source': base64.b64encode(b'invalid').decode(), 'preset': 'audio', 'duration': 1})
                assert status == 202 and finish(job['id'])['status'] == 'failed'
                assert call('/jobs', {'source': encoded, 'preset': 'audio', 'duration': -1})[0] == 400
            finally:
                server.shutdown()
                thread.join()
                manager.close()
        manager = JobManager(Path(tmp) / 'data', workers=1)
        try:
            assert manager.get(ids[0])['status'] == 'succeeded'
            assert manager.result(ids[0])['sha256']
        finally:
            manager.close()
        manager = JobManager(Path(tmp) / 'data', workers=0)
        try:
            queued = manager.submit({'source': encoded, 'preset': 'audio', 'duration': 1})
            assert manager.cancel(queued['id'])['status'] == 'cancelled'
            interrupted = manager.submit({'source': encoded, 'preset': 'audio', 'duration': 1})
            assert manager.claim() == interrupted['id']
        finally:
            manager.close()
        manager = JobManager(Path(tmp) / 'data', workers=0)
        try:
            assert manager.get(interrupted['id'])['status'] == 'failed'
            assert manager.get(interrupted['id'])['error'] == 'interrupted by service restart'
        finally:
            manager.close()
    print('media jobs: ok')


if __name__ == '__main__':
    main()
