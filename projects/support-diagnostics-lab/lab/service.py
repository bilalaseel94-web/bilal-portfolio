"""Synthetic loopback fixture; never an operational monitoring endpoint."""
import argparse
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class LabServer(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/health':
            code, payload = 404, {'error': 'not-found'}
        else:
            healthy = self.server.mode == 'healthy'
            code = 200 if healthy else 503
            payload = {'service': 'support-diagnostics-lab',
                       'status': 'ok' if healthy else 'unavailable'}
        body = json.dumps(payload).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def create_server(port: int, mode: str) -> ThreadingHTTPServer:
    if mode not in {'healthy', 'unavailable'}:
        raise ValueError('Mode must be healthy or unavailable')
    if not 0 <= port <= 65535:
        raise ValueError('Port must be between 0 and 65535')
    server = LabServer(('127.0.0.1', port), Handler)
    server.mode = mode
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--mode', choices=['healthy', 'unavailable'], default='healthy')
    args = parser.parse_args()
    try:
        server = create_server(args.port, args.mode)
    except (OSError, ValueError) as error:
        parser.exit(2, f'Cannot start lab service: {error}\nChoose an unused port; no existing process was stopped.\n')
    print(f'Lab fixture: http://127.0.0.1:{server.server_port}/health ({args.mode}). Ctrl+C stops it.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
