from contextlib import contextmanager
import json
from pathlib import Path
import queue
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from test_checks import ROOT, PWSH


@contextmanager
def fixture(mode='healthy'):
    process = subprocess.Popen([sys.executable, str(ROOT / 'lab/service.py'), '--port', '0', '--mode', mode],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
    lines = queue.Queue()
    reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
    reader.start()
    try:
        line = lines.get(timeout=5)
        match = re.search(r'127\.0\.0\.1:(\d+)', line)
        if not match: raise AssertionError(f'Fixture did not start: {line}')
        yield int(match.group(1)), process
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=5)
        reader.join(1)
        process.stdout.close(); process.stderr.close()


def cli(port, output, target='localhost'):
    return subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-File', str(ROOT / 'Invoke-SupportCheck.ps1'),
        '-TargetName', target, '-Port', str(port), '-OutputDirectory', str(output)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=20)


class CliIntegrationTests(unittest.TestCase):
    def test_healthy_stopped_and_unavailable_preserve_reports(self):
        with tempfile.TemporaryDirectory(prefix='support-lab-cli-') as folder:
            with fixture() as (port, _):
                result = cli(port, folder)
                self.assertEqual(result.returncode, 0, result.stderr)
                paths = json.loads(result.stdout)
                original = Path(paths['JsonPath']).read_bytes()
                healthy = json.loads(original)
                self.assertEqual(healthy['finding'], 'healthy')
                self.assertIn(healthy['runId'], Path(paths['HtmlPath']).read_text('utf-8'))
            stopped = cli(port, folder)
            self.assertEqual(stopped.returncode, 1, stopped.stderr)
            stopped_report = json.loads(Path(json.loads(stopped.stdout)['JsonPath']).read_text('utf-8'))
            self.assertEqual(stopped_report['stages'][2]['status'], 'skipped')
            with fixture('unavailable') as (port, _):
                result = cli(port, folder)
                self.assertEqual(result.returncode, 1, result.stderr)
                report = json.loads(Path(json.loads(result.stdout)['JsonPath']).read_text('utf-8'))
                self.assertEqual(report['finding'], 'application-unavailable')
                self.assertEqual(report['stages'][1]['status'], 'success')
            self.assertEqual(original, Path(paths['JsonPath']).read_bytes())
            self.assertEqual(len(list(Path(folder).glob('*.json'))), 3)

    def test_cleanup_even_when_caller_fails(self):
        captured = None
        with self.assertRaisesRegex(RuntimeError, 'intentional'):
            with fixture() as (_, process):
                captured = process
                raise RuntimeError('intentional caller failure')
        self.assertIsNotNone(captured.poll())

    def test_save_failure_is_not_network_failure(self):
        with tempfile.TemporaryDirectory(prefix='support-lab-cli-') as folder:
            blocked = Path(folder) / 'file'; blocked.write_text('keep', encoding='utf-8')
            with fixture() as (port, _):
                result = cli(port, blocked)
            self.assertEqual(result.returncode, 2)
            self.assertIn("observed finding remains 'healthy'", result.stderr)
            fallback = json.loads(result.stdout)
            self.assertFalse(fallback['reportSaved'])
            self.assertEqual(fallback['evidence']['finding'], 'healthy')
            self.assertEqual([stage['status'] for stage in fallback['evidence']['stages']], ['success'] * 3)
            self.assertEqual(fallback['evidence']['stages'][2]['facts']['statusCode'], 200)
            self.assertEqual(blocked.read_text(), 'keep')

    def test_invalid_inputs_have_exit_two(self):
        with tempfile.TemporaryDirectory(prefix='support-lab-cli-') as folder:
            for port, target in [('word', 'localhost'), (0, 'localhost'), (8765, 'example.com')]:
                result = cli(port, folder, target)
                self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(list(Path(folder).iterdir()), [])
