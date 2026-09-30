import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
PWSH = os.environ.get('SUPPORT_LAB_PWSH') or shutil.which('pwsh')


def check(port):
    result = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-Command',
        f"$ErrorActionPreference='Stop'; Import-Module ./src/SupportDiagnostics.psm1; "
        f"Get-SupportEvidence -TargetName localhost -Port {port} | ConvertTo-Json -Depth 10 -Compress"],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=15)
    if result.returncode:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


class EdgeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        scenario = self.server.scenario
        if scenario == 'slow-headers':
            time.sleep(6)
        code = 302 if scenario == 'redirect' else 200
        body = b'{"service":"support-diagnostics-lab","status":"ok"}'
        if scenario == 'wrong-service': body = b'{"service":"other","status":"ok"}'
        if scenario == 'invalid-json': body = b'not json'
        if scenario == 'array-identity': body = b'{"service":["other","support-diagnostics-lab"],"status":["unavailable","ok"]}'
        if scenario == 'array-status': body = b'{"service":"support-diagnostics-lab","status":["unavailable","ok"]}'
        if scenario == 'large': body = b'x' * 8193
        if scenario == 'unavailable':
            code, body = 503, b'{"service":"support-diagnostics-lab","status":"unavailable"}'
        self.server.requests += 1
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            if code == 302: self.send_header('Location', 'http://127.0.0.1:1/should-not-follow')
            self.end_headers()
            if scenario == 'slow-body': time.sleep(6)
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def log_message(self, *args): pass


class CheckIntegrationTests(unittest.TestCase):
    def run_scenario(self, scenario):
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), EdgeHandler)
        server.daemon_threads = True
        server.scenario, server.requests = scenario, 0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = check(server.server_port)
            return result, server.requests
        finally:
            server.shutdown(); server.server_close(); thread.join(2)

    def test_real_healthy(self):
        result, _ = self.run_scenario('healthy')
        self.assertEqual(result['finding'], 'healthy')
        self.assertEqual([x['status'] for x in result['stages']], ['success'] * 3)

    def test_real_unavailable(self):
        result, _ = self.run_scenario('unavailable')
        self.assertEqual(result['finding'], 'application-unavailable')
        self.assertEqual(result['stages'][1]['status'], 'success')
        self.assertEqual(result['stages'][2]['facts']['statusCode'], 503)

    def test_wrong_service(self):
        self.assertEqual(self.run_scenario('wrong-service')[0]['finding'], 'unexpected-service')

    def test_invalid_json(self):
        self.assertEqual(self.run_scenario('invalid-json')[0]['finding'], 'unexpected-service')

    def test_array_identity_rejected(self):
        self.assertEqual(self.run_scenario('array-identity')[0]['finding'], 'unexpected-service')

    def test_array_status_rejected(self):
        self.assertEqual(self.run_scenario('array-status')[0]['finding'], 'unexpected-application-response')

    def test_large_body(self):
        self.assertEqual(self.run_scenario('large')[0]['finding'], 'response-too-large')

    def test_no_redirect(self):
        result, requests = self.run_scenario('redirect')
        self.assertEqual(result['finding'], 'redirect-not-followed')
        self.assertEqual(requests, 1)

    def test_header_deadline(self):
        result, _ = self.run_scenario('slow-headers')
        self.assertEqual(result['finding'], 'http-timeout')
        self.assertLess(result['stages'][2]['durationMs'], 6500)

    def test_body_deadline(self):
        result, _ = self.run_scenario('slow-body')
        self.assertEqual(result['finding'], 'http-timeout')
        self.assertLess(result['stages'][2]['durationMs'], 6500)
