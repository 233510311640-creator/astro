from pathlib import Path
import copy
import hashlib
import io
import json
import re
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from local_assistant import runtime_worker as rw

ROOT = Path(__file__).resolve().parents[1]
NAME = 'qwen3.5:9b-q4_K_M'


def installed():
    return {'name': NAME, 'model': NAME, 'size': 8 * 2**30, 'details': {'format': 'gguf'}}


def metrics():
    return {'done': True, 'done_reason': 'stop', 'model': NAME, 'response': 'PRIVATE GENERATED WORDS',
            'thinking': 'PRIVATE THINKING', 'total_duration': 3 * 10**9, 'load_duration': 10**9,
            'prompt_eval_count': 12, 'prompt_eval_duration': 100000000, 'eval_count': 20, 'eval_duration': 10**9}


class FakeTransport:
    def __init__(self):
        self.calls = []; self.items = [installed()]; self.loaded = []
        self.show = {'model_info': {'general.architecture': 'qwen35'}}
        self.generated = metrics(); self.failure = None
    def request(self, path, payload=None):
        self.calls.append((path, copy.deepcopy(payload)))
        if path == self.failure: raise rw.RuntimeFault('FIXTURE_FAILURE')
        if path == '/api/version': return {'version': '0.12.0'}
        if path == '/api/tags': return {'models': self.items}
        if path == '/api/ps': return {'models': self.loaded}
        if path == '/api/show': return self.show
        if path == '/api/generate': return self.generated
        raise AssertionError(path)


class RuntimeWorkerTests(unittest.TestCase):
    def test_status_does_not_generate_load_unload_or_download(self):
        transport = FakeTransport()
        state, text = rw.run('status', NAME, transport)
        self.assertEqual(state, 'COMPLETED')
        self.assertIn('No generation ran', text)
        self.assertIn('Not observed in loaded models', text)
        self.assertEqual([p for p, _ in transport.calls], ['/api/version', '/api/tags', '/api/ps'])
        self.assertTrue(all(payload is None for _, payload in transport.calls))

    def test_benchmark_exactly_one_generation_preserves_selected_model(self):
        transport = FakeTransport()
        state, text = rw.run('benchmark', NAME, transport)
        self.assertEqual(state, 'COMPLETED')
        self.assertIn('20.0 tokens/s', text)
        calls = [v for p, v in transport.calls if p == '/api/generate']
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['model'], NAME)
        self.assertEqual(calls[0]['options']['num_predict'], 64)
        self.assertEqual(calls[0]['options']['num_ctx'], 4096)
        self.assertFalse(calls[0]['stream'])
        for key in ('keep_alive', 'tools', 'context', 'images'): self.assertNotIn(key, calls[0])
        self.assertNotIn('PRIVATE', text)
        self.assertIn('not a controlled cold/warm test', text)

    def test_missing_model_does_not_trigger_generation(self):
        transport = FakeTransport(); transport.items = []
        with self.assertRaisesRegex(rw.RuntimeFault, 'SELECTED_MODEL_NOT_INSTALLED'): rw.run('benchmark', NAME, transport)
        self.assertNotIn('/api/generate', [p for p, _ in transport.calls])
        self.assertEqual(rw.run('status', NAME, FakeTransport())[0], 'COMPLETED')

    def test_cloud_aliases_and_unknown_weight_format_are_rejected(self):
        for changes in ({'remote_model': 'remote'}, {'remote_host': 'https://remote.example'}, {'size': 0}, {'details': {'format': 'remote'}}):
            transport = FakeTransport(); transport.items[0].update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(rw.RuntimeFault, 'LOCAL_MODEL_NOT_VERIFIED'):
                rw.run('benchmark', NAME, transport)
            self.assertNotIn('/api/generate', [p for p, _ in transport.calls])

    def test_show_revalidates_alias_before_synthetic_prompt(self):
        for value in ({'remote_host': 'https://remote.example'}, {'remote_model': 'remote'}, {'model_info': {}}, {'model_info': []}):
            transport = FakeTransport(); transport.show = value
            with self.subTest(value=value), self.assertRaisesRegex(rw.RuntimeFault, 'LOCAL_MODEL_NOT_VERIFIED'):
                rw.run('benchmark', NAME, transport)
            self.assertNotIn('/api/generate', [p for p, _ in transport.calls])

    def test_connection_failure_never_retries_or_switches(self):
        transport = FakeTransport(); transport.failure = '/api/generate'
        with self.assertRaisesRegex(rw.RuntimeFault, 'FIXTURE_FAILURE'): rw.run('benchmark', NAME, transport)
        self.assertEqual(sum(p == '/api/generate' for p, _ in transport.calls), 1)

    def test_after_snapshot_failure_retains_generation_metrics_as_partial(self):
        transport = FakeTransport(); request = transport.request
        def fail_after(path, payload=None):
            if path == '/api/ps' and any(p == '/api/generate' for p, _ in transport.calls):
                raise rw.RuntimeFault('SNAPSHOT_UNAVAILABLE')
            return request(path, payload)
        transport.request = fail_after
        state, text = rw.run('benchmark', NAME, transport)
        self.assertEqual(state, 'PARTIAL')
        self.assertIn('20.0 tokens/s', text)
        self.assertIn('After-residency unavailable', text)
        self.assertEqual(sum(p == '/api/generate' for p, _ in transport.calls), 1)

    def test_stop_after_generation_prevents_a_success_claim(self):
        transport = FakeTransport(); request = transport.request
        def stop_after(path, payload=None):
            if path == '/api/ps' and any(p == '/api/generate' for p, _ in transport.calls):
                raise rw.RuntimeFault('STOP_REQUESTED')
            return request(path, payload)
        transport.request = stop_after
        with self.assertRaisesRegex(rw.RuntimeFault, 'STOP_REQUESTED'): rw.run('benchmark', NAME, transport)
        self.assertEqual(sum(p == '/api/generate' for p, _ in transport.calls), 1)

    def test_incomplete_or_wrong_model_or_tool_response_is_rejected(self):
        for change in ({'done': False}, {'model': 'other:latest'}, {'remote_host': 'remote'}, {'tool_calls': [{}]}, {'response': None}):
            value = metrics(); value.update(change)
            with self.subTest(change=change), self.assertRaises(rw.RuntimeFault): rw.measurement(value, NAME)

    def test_invalid_numeric_metrics_are_not_reported_as_measurements(self):
        for change in ({'eval_count': True}, {'eval_count': -1}, {'eval_duration': 0}, {'eval_duration': float('nan')},
                       {'total_duration': 1}, {'load_duration': '123'}, {'prompt_eval_count': 1000000}):
            value = metrics(); value.update(change)
            with self.subTest(change=change), self.assertRaises(rw.RuntimeFault): rw.measurement(value, NAME)

    def test_token_limit_is_disclosed_and_not_quality_pass(self):
        value = metrics(); value['done_reason'] = 'length'
        self.assertIn('64-token budget', rw.measurement(value, NAME)[0])

    def test_residency_is_snapshot_in_gib_not_peak_or_percent_guess(self):
        self.assertIn('2.00 GiB', rw.residency({'size_vram': 2 * 2**30, 'context_length': 4096}))
        self.assertIn('0.00 GiB', rw.residency({'size_vram': 0}))
        for value in (None, -1, True):
            with self.assertRaises(rw.RuntimeFault): rw.residency({'size_vram': value})

    def test_duplicate_and_invalid_json_rejected(self):
        for raw in ('{"x":1,"x":2}', '{"x":NaN}', '[]', '{bad'):
            with self.assertRaises(rw.RuntimeFault): rw.decode(raw)

    def test_ambiguous_model_records_are_rejected(self):
        for items in ([installed(), installed()], [{'name': NAME, 'model': 'other'}], [installed()] * 129):
            with self.assertRaises(rw.RuntimeFault): rw.records({'models': items})

    def test_unknown_commands_do_not_access_network(self):
        for command in ('help', 'load', 'pull', 'benchmark twice'):
            transport = FakeTransport(); rw.run(command, NAME, transport)
            self.assertEqual(transport.calls, [])

    def test_model_names_cannot_be_urls_or_path_traversals(self):
        for name in ('https://remote/model', '../model', '/model', 'model\nheader'):
            with self.assertRaises(rw.RuntimeFault): rw.model_name(name)

    def test_loopback_refuses_endpoint_and_method_changes_before_connection(self):
        transport = rw.Loopback(threading.Event(), 15)
        with patch.object(rw.http.client, 'HTTPConnection') as connection:
            for path, payload in (('/api/pull', {}), ('https://remote.example', None), ('/api/ps', {}), ('/api/generate', None)):
                with self.assertRaises(rw.RuntimeFault): transport.request(path, payload)
            connection.assert_not_called()

    def test_stop_before_request_prevents_connection(self):
        event = threading.Event(); event.set()
        with patch.object(rw.http.client, 'HTTPConnection') as connection:
            with self.assertRaisesRegex(rw.RuntimeFault, 'STOP_REQUESTED'): rw.Loopback(event, 15).request('/api/ps')
            connection.assert_not_called()

    def test_http_transport_uses_fixed_loopback_and_refuses_redirect(self):
        with patch.object(rw.http.client, 'HTTPConnection') as factory:
            response = factory.return_value.getresponse.return_value; response.status = 302
            with self.assertRaisesRegex(rw.RuntimeFault, 'OLLAMA_HTTP_302_AT_PS'):
                rw.Loopback(threading.Event(), 15).request('/api/ps')
            self.assertEqual(factory.call_args.args, ('127.0.0.1', 11434))
            self.assertEqual(factory.return_value.request.call_count, 1)
            factory.return_value.close.assert_called_once()

    def test_http_body_is_capped_and_wrong_content_type_rejected(self):
        for headers in ({'Content-Type': 'text/html'}, {'Content-Type': 'application/json', 'Content-Length': '262145'},
                        {'Content-Type': 'application/json', 'Content-Encoding': 'gzip'}):
            with patch.object(rw.http.client, 'HTTPConnection') as factory:
                response = factory.return_value.getresponse.return_value; response.status = 200
                response.getheader.side_effect = lambda name, default=None: headers.get(name, default)
                with self.assertRaises(rw.RuntimeFault): rw.Loopback(threading.Event(), 15).request('/api/ps')
                response.read1.assert_not_called()

    def test_http_success_reads_bounded_json_without_credentials(self):
        with patch.object(rw.http.client, 'HTTPConnection') as factory:
            response = factory.return_value.getresponse.return_value; response.status = 200
            response.getheader.side_effect = lambda name, default=None: {'Content-Type': 'application/json'}.get(name, default)
            response.read1.side_effect = [b'{"models":[]}', b'']
            self.assertEqual(rw.Loopback(threading.Event(), 15).request('/api/ps'), {'models': []})
            args = factory.return_value.request.call_args.args
            self.assertEqual(args[:3], ('GET', '/api/ps', None))
            self.assertEqual(set(args[3]), {'Accept', 'Content-Type', 'Connection'})

    def test_stop_during_connection_prevents_http_request(self):
        event = threading.Event()
        with patch.object(rw.http.client, 'HTTPConnection') as factory:
            factory.return_value.connect.side_effect = event.set
            with self.assertRaisesRegex(rw.RuntimeFault, 'STOP_REQUESTED'):
                rw.Loopback(event, 15).request('/api/generate', {'model': NAME})
            factory.return_value.request.assert_not_called()

    def test_native_runtime_worker_pin_and_installer_order(self):
        client = (ROOT/'windows/Cypher.CorePreview/FileTaskClient.cs').read_text(encoding='utf-8')
        pin = re.search('RuntimeWorkerSha256 = "([a-f0-9]{64})";', client)[1]
        self.assertEqual(pin, hashlib.sha256((ROOT/'src/local_assistant/runtime_worker.py').read_bytes()).hexdigest())
        installer = (ROOT/'scripts/install_cypher_core_preview_windows.ps1').read_text(encoding='utf-8')
        self.assertLess(installer.index('$runtimeSelfTest ='), installer.index('\n    Stop-LegacyHost\n'))

    def test_actual_isolated_entrypoint_offline_fixture(self):
        request = {'input': 'Runtime: self-test', 'model': NAME, 'nonce': 'a' * 32}
        result = subprocess.run([sys.executable, '-I', '-S', '-B', '-X', 'utf8', str(ROOT/'src/local_assistant/runtime_worker.py')],
                                input=json.dumps(request)+'\n', capture_output=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'type': 'result', 'nonce': 'a'*32, 'state': 'COMPLETED', 'text': 'RUNTIME_SELF_TEST_OK'})
        self.assertEqual(result.stderr, '')


if __name__ == '__main__': unittest.main()
