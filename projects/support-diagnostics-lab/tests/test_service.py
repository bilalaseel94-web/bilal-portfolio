import http.client
import json
import threading
import unittest
from lab.service import create_server


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server(0, 'healthy')
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(2)
        self.assertFalse(self.thread.is_alive())

    def request(self, path='/health'):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=2)
        try:
            conn.request('GET', path)
            response = conn.getresponse()
            return response.status, json.loads(response.read())
        finally:
            conn.close()

    def test_healthy(self):
        status, data = self.request()
        self.assertEqual(status, 200)
        self.assertEqual(data, {'service': 'support-diagnostics-lab', 'status': 'ok'})

    def test_unavailable(self):
        self.server.mode = 'unavailable'
        status, data = self.request()
        self.assertEqual(status, 503)
        self.assertEqual(data['status'], 'unavailable')

    def test_wrong_path(self):
        self.assertEqual(self.request('/other')[0], 404)

    def test_port_collision_preserves_first_server(self):
        with self.assertRaises(OSError):
            create_server(self.server.server_port, 'healthy')
        self.assertEqual(self.request()[0], 200)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            create_server(0, 'invented')
