"""Bounded native runtime checks: fixed loopback only; no files, tools or saved model text."""
from __future__ import annotations

import http.client
import json
import os
import re
import socket
import sys
import threading
import time

MODEL = re.compile(r'[A-Za-z0-9][A-Za-z0-9_./:-]{0,127}')
HELP = ('Local runtime\n\nRuntime: status — check Ollama and model residency without generating.\n'
        'Runtime: benchmark — one short synthetic generation using the selected installed model.\n\n'
        'Auto/Fast uses the configured Fast model; Deep uses the configured Deep model. '
        'No download, model substitution, unload, retry or saved answer. '
        'GPU figures are Ollama-reported residency snapshots, not whole-GPU or peak usage.')


class RuntimeFault(Exception):
    pass


def model_name(value):
    if not isinstance(value, str) or not MODEL.fullmatch(value) or '://' in value or '..' in value or value.startswith('/'):
        raise RuntimeFault('MODEL_NAME_INVALID')
    return value


def canonical_model(value):
    value = model_name(value)
    return value if ':' in value.rsplit('/', 1)[-1] else value + ':latest'


def integer(value, maximum=2**60):
    if type(value) is not int or value < 0 or value > maximum:
        raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
        result[key] = value
    return result


def decode(data):
    try:
        value = json.loads(data, object_pairs_hook=unique_object,
                           parse_constant=lambda x: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RuntimeFault('RUNTIME_RESPONSE_INVALID') from exc
    if not isinstance(value, dict): raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
    return value


class Loopback:
    def __init__(self, stopped, seconds):
        self.stopped = stopped
        self.deadline = time.monotonic() + seconds
        self.connection = None

    def stop(self):
        self.stopped.set()
        connection = self.connection
        try:
            if connection and connection.sock: connection.sock.shutdown(socket.SHUT_RDWR)
        except OSError: pass

    def request(self, path, payload=None):
        if path not in {'/api/version', '/api/tags', '/api/ps', '/api/show', '/api/generate'}:
            raise RuntimeFault('ENDPOINT_BLOCKED')
        if (payload is None) != (path in {'/api/version', '/api/tags', '/api/ps'}):
            raise RuntimeFault('METHOD_BLOCKED')
        if self.stopped.is_set(): raise RuntimeFault('STOP_REQUESTED')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0: raise RuntimeFault('RUNTIME_TIME_LIMIT')
        connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=min(remaining, 2))
        self.connection = connection
        try:
            connection.connect()
            if self.stopped.is_set(): raise RuntimeFault('STOP_REQUESTED')
            remaining = self.deadline - time.monotonic()
            if remaining <= 0: raise RuntimeFault('RUNTIME_TIME_LIMIT')
            connection.sock.settimeout(min(remaining, 90 if path == '/api/generate' else 5))
            body = None if payload is None else json.dumps(payload, ensure_ascii=True).encode('ascii')
            connection.request('GET' if body is None else 'POST', path, body,
                               {'Accept': 'application/json', 'Content-Type': 'application/json', 'Connection': 'close'})
            response = connection.getresponse()
            if response.status != 200: raise RuntimeFault('OLLAMA_HTTP_' + str(response.status) + '_AT_' + path.rsplit('/', 1)[-1].upper())
            if response.getheader('Content-Type', '').split(';')[0].strip().lower() != 'application/json':
                raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
            limit = 1048576 if path == '/api/show' else 262144
            if response.getheader('Content-Encoding', 'identity') != 'identity': raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
            length = response.getheader('Content-Length')
            if length is not None and (not length.isdigit() or int(length) > limit): raise RuntimeFault('RUNTIME_RESPONSE_TOO_LARGE')
            chunks, total = [], 0
            while True:
                if self.stopped.is_set(): raise RuntimeFault('STOP_REQUESTED')
                if time.monotonic() >= self.deadline: raise RuntimeFault('RUNTIME_TIME_LIMIT')
                chunk = response.read1(min(8192, limit + 1 - total))
                if not chunk: break
                total += len(chunk)
                if total > limit: raise RuntimeFault('RUNTIME_RESPONSE_TOO_LARGE')
                chunks.append(chunk)
            return decode(b''.join(chunks))
        except (TimeoutError, socket.timeout) as exc:
            raise RuntimeFault('RUNTIME_TIME_LIMIT') from exc
        except (OSError, http.client.HTTPException) as exc:
            raise RuntimeFault('STOP_REQUESTED' if self.stopped.is_set() else 'OLLAMA_CONNECTION_FAILED') from exc
        finally:
            connection.close()
            self.connection = None


def records(value):
    items = value.get('models')
    if not isinstance(items, list) or len(items) > 128: raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
    result = {}
    for item in items:
        if not isinstance(item, dict): raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
        name = model_name(item.get('name'))
        if 'model' in item and canonical_model(item['model']) != canonical_model(name):
            raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
        key = canonical_model(name)
        if key in result: raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
        result[key] = item
    return result


def local_record(item):
    return (not item.get('remote_host') and not item.get('remote_model') and 'cloud' not in item['name'].lower()
            and type(item.get('size')) is int and 0 < item['size'] < 2**50
            and isinstance(item.get('details'), dict) and item['details'].get('format') == 'gguf')


def residency(item):
    if item is None: return 'Not observed in loaded models'
    amount = integer(item.get('size_vram'))
    context = item.get('context_length')
    line = 'Loaded; reported GPU memory ' + format(amount / 2**30, '.2f') + ' GiB'
    if context is not None: line += '; context ' + str(integer(context, 2**24)) + ' tokens'
    return line


def measurement(value, requested):
    if (value.get('done') is not True or canonical_model(value.get('model')) != canonical_model(requested)
            or value.get('remote_host') or value.get('remote_model') or value.get('tool_calls')
            or not isinstance(value.get('response'), str) or len(value['response']) > 65536):
        raise RuntimeFault('GENERATION_RESPONSE_INVALID')
    if value.get('done_reason') not in {'stop', 'length'}: raise RuntimeFault('GENERATION_RESPONSE_INVALID')
    output = integer(value.get('eval_count'), 128)
    duration = integer(value.get('eval_duration'), 600 * 10**9)
    total = integer(value.get('total_duration'), 600 * 10**9)
    load = integer(value.get('load_duration'), 600 * 10**9)
    prompt = integer(value.get('prompt_eval_duration'), 600 * 10**9)
    integer(value.get('prompt_eval_count'), 65536)
    if output == 0 or duration == 0 or total < max(duration, load, prompt):
        raise RuntimeFault('GENERATION_METRICS_INVALID')
    return ['Generation: ' + ('finished' if value['done_reason'] == 'stop' else 'finished at the 64-token budget'),
            'Server total: ' + format(total / 1e9, '.2f') + ' s',
            'Model loading: ' + format(load / 1e9, '.2f') + ' s',
            'Prompt evaluation: ' + format(prompt / 1e9, '.2f') + ' s',
            'Output: ' + str(output) + ' tokens; ' + format(output / (duration / 1e9), '.1f') + ' tokens/s']


def run(command, selected, transport):
    selected = model_name(selected)
    key = canonical_model(selected)
    if command == 'help': return 'COMPLETED', HELP
    if command not in {'status', 'benchmark'}: return 'REJECTED', HELP
    version = transport.request('/api/version').get('version')
    if not isinstance(version, str) or not re.fullmatch(r'[0-9]+\.[0-9]+(?:\.[0-9]+)?(?:[-+][A-Za-z0-9._-]+)?', version):
        raise RuntimeFault('RUNTIME_RESPONSE_INVALID')
    available = records(transport.request('/api/tags'))
    loaded = records(transport.request('/api/ps'))
    item = available.get(key)
    lines = ['Local runtime status', '', 'Ollama: reachable (' + version + ')', 'Selected model: ' + selected,
             'Installation: ' + ('not found' if item is None else 'local GGUF observed' if local_record(item) else 'local weights not verified'),
             'Residency: ' + residency(loaded.get(key))]
    if command == 'status':
        lines += ['', 'Loaded models: ' + str(len(loaded))]
        for name, record in list(loaded.items())[:16]: lines.append(name + ' — ' + residency(record))
        if len(loaded) > 16: lines.append('Only the first 16 loaded models are shown.')
        lines += ['', 'No generation ran. For a short measured generation, send Runtime: benchmark.',
                  'GPU values are Ollama residency snapshots, not peak or whole-GPU usage.']
        return ('COMPLETED' if item and local_record(item) else 'PARTIAL'), '\n'.join(lines)
    if item is None: raise RuntimeFault('SELECTED_MODEL_NOT_INSTALLED')
    if not local_record(item): raise RuntimeFault('LOCAL_MODEL_NOT_VERIFIED')
    show = transport.request('/api/show', {'model': selected})
    if (show.get('remote_host') or show.get('remote_model') or not isinstance(show.get('model_info'), dict)
            or not isinstance(show['model_info'].get('general.architecture'), str)
            or not show['model_info']['general.architecture']):
        raise RuntimeFault('LOCAL_MODEL_NOT_VERIFIED')
    # One synthetic call only. Defaults for thinking/keep-alive remain the server's own.
    payload = {'model': selected, 'prompt': 'Reply briefly with READY.', 'stream': False,
               'options': {'temperature': 0, 'num_ctx': 4096, 'num_predict': 64}}
    start = time.monotonic()
    value = transport.request('/api/generate', payload)
    metrics = measurement(value, selected)
    # Response/thinking/context are never added to a report, log, model history or file.
    del value
    lines += ['', 'One-generation performance check', 'Client generation request: ' + format(time.monotonic() - start, '.2f') + ' s'] + metrics
    state = 'COMPLETED'
    try:
        after = records(transport.request('/api/ps'))
        lines += ['After: ' + residency(after.get(key))]
    except RuntimeFault as exc:
        if str(exc) == 'STOP_REQUESTED': raise
        state = 'PARTIAL'
        lines += ['After-residency unavailable (' + str(exc) + '). Generation metrics above remain valid.']
    lines += ['', 'Initial residency is an observation, not a controlled cold/warm test. The model may load or resize its context.',
              'GPU figures are snapshots, not peak usage. This short test does not measure answer quality.',
              'One generation; no download, fallback, retry, unload or saved generated text.']
    return state, '\n'.join(lines)


def self_test():
    class Fixture:
        def __init__(self): self.calls = []
        def request(self, path, payload=None):
            self.calls.append(path)
            if path == '/api/version': return {'version': '0.12.0'}
            if path == '/api/tags': return {'models': [{'name': 'fixture:latest', 'size': 123, 'details': {'format': 'gguf'}}]}
            if path == '/api/ps': return {'models': []}
            raise RuntimeFault('UNEXPECTED_FIXTURE_REQUEST')
    fixture = Fixture()
    state, text = run('status', 'fixture', fixture)
    assert state == 'COMPLETED' and 'No generation ran' in text
    assert fixture.calls == ['/api/version', '/api/tags', '/api/ps']
    try: decode('{"version":"a","version":"b"}')
    except RuntimeFault: pass
    else: raise AssertionError('Duplicate JSON accepted')


def serve(reader, writer):
    line = reader.readline(16385)
    if len(line) > 16384 or not line.endswith('\n'): raise RuntimeFault('REQUEST_INVALID')
    request = decode(line)
    if set(request) != {'input', 'nonce', 'model'}: raise RuntimeFault('REQUEST_INVALID')
    nonce = request['nonce']
    if not isinstance(nonce, str) or not re.fullmatch('[a-f0-9]{32}', nonce): raise RuntimeFault('REQUEST_INVALID')
    model_name(request['model'])
    match = re.fullmatch(r'\s*Runtime\s*:\s*(status|benchmark|help|self-test)\s*', request['input'], re.I) if isinstance(request['input'], str) else None
    stopped = threading.Event()
    transport = Loopback(stopped, 90 if match and match[1].lower() == 'benchmark' else 15)
    def listen():
        try:
            control = decode(reader.readline(4097))
            if control != {'nonce': nonce, 'command': 'stop'}: transport.stop(); return
        except Exception: pass
        transport.stop()
    if match and match[1].lower() == 'self-test':
        self_test(); state, text = 'COMPLETED', 'RUNTIME_SELF_TEST_OK'
    else:
        threading.Thread(target=listen, daemon=True).start()
        try:
            state, text = run(match[1].lower() if match else 'invalid', request['model'], transport)
            if stopped.is_set(): raise RuntimeFault('STOP_REQUESTED')
        except RuntimeFault as exc:
            code = 'STOP_REQUESTED' if stopped.is_set() else str(exc)
            state = 'CANCELLED' if code == 'STOP_REQUESTED' else 'FAILED'
            text = ('Runtime check cancelled. No further requests will run. An already submitted Ollama generation may still finish on the server.'
                    if state == 'CANCELLED' else 'Runtime check could not finish. Diagnostic: ' + code + '. No retry, download or model substitution ran.')
    writer.write(json.dumps({'type': 'result', 'nonce': nonce, 'state': state, 'text': text}, ensure_ascii=True) + '\n')
    writer.flush()
    return 0


if __name__ == '__main__':
    try: code = serve(sys.stdin, sys.stdout)
    except Exception: code = 1
    os._exit(code)  # Terminal frame is flushed; stdin listener must not race buffered IO finalization.
