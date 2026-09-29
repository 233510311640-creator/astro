from pathlib import Path
import io
import json
import queue
import tempfile
import threading
import unittest
from unittest.mock import patch

from local_assistant.file_tasks import FileTasks, serve, tokens
from local_assistant.file_tasks_selftest import run
from local_assistant.operator_engine import OperatorStateStore, OperatorCancelled
from local_assistant.permission_center import PermissionRootStore, SUPPORTED_CAPABILITIES
from local_assistant.protected_payload import TestKeyProtector
from local_assistant.capability_broker import BrokerPolicyViolation


class FileTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'Approved Fixture'
        self.root.mkdir()
        self.store = PermissionRootStore(self.base / 'permissions.json', home=self.base / 'Unrelated Home', environment={})
        self.store.add('fixture', self.root, sorted(SUPPORTED_CAPABILITIES))
        self.protector = TestKeyProtector(self.base / 'key')
        self.state = OperatorStateStore(self.base / 'state.db', self.protector)
        self.service = FileTasks(self.store, self.state, self.base / 'Quarantine')

    def execute(self, review, stopped=lambda: False, progress=lambda *a: None):
        return self.service.execute(review, review['fingerprint'], stopped, progress)

    def test_full_organize_undo_stop_fixture(self):
        run(self.protector)

    def test_create_full_text_and_replace_undo(self):
        body = 'quotes " remain\nUnicode: \u00e9'
        review = self.service.prepare('Files: create fixture "note.txt" : ' + body)
        self.assertIn('Unicode:', review['text'])
        self.assertFalse((self.root / 'note.txt').exists())
        self.execute(review)
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), body)
        self.execute(self.service.prepare('Files: replace fixture "note.txt" : replacement'))
        self.execute(self.service.prepare('Files: undo last'))
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), body)

    def test_denial_and_wrong_fingerprint_never_execute(self):
        review = self.service.prepare('Files: mkdir fixture "Folder"')
        with self.assertRaises(BrokerPolicyViolation):
            self.service.execute(review, '0' * 64, lambda: False, lambda *a: None)
        self.service.reject(review)
        with self.assertRaises(BrokerPolicyViolation): self.execute(review)
        self.assertFalse((self.root / 'Folder').exists())

    def test_cancel_between_approval_and_claim_consumes_permission(self):
        review = self.service.prepare('Files: mkdir fixture "Folder"')
        op = self.service.operator()
        self.state.approve(review['id'], review['fingerprint'])
        with self.assertRaises(OperatorCancelled): op.apply(review['id'], cancelled=lambda: True)
        self.assertEqual(self.state.get_plan(review['id']).status, 'cancelled_rolled_back')
        with self.assertRaises(BrokerPolicyViolation): op.apply(review['id'])
        self.assertFalse((self.root / 'Folder').exists())

    def test_revoked_permission_blocks_apply(self):
        review = self.service.prepare('Files: mkdir fixture "Folder"')
        self.store.remove('fixture')
        with self.assertRaises(BrokerPolicyViolation): self.execute(review)
        self.assertFalse((self.root / 'Folder').exists())

    def test_collision_rejected_before_any_change(self):
        (self.root / 'Documents').mkdir()
        (self.root / 'Documents/note.txt').write_text('destination', encoding='utf-8')
        (self.root / 'note.txt').write_text('source', encoding='utf-8')
        with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: organize fixture')
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), 'source')
        self.assertEqual((self.root / 'Documents/note.txt').read_text(encoding='utf-8'), 'destination')

    def test_destination_appearing_after_review_is_preserved(self):
        (self.root / 'note.txt').write_text('source', encoding='utf-8')
        review = self.service.prepare('Files: organize fixture')
        (self.root / 'Documents').mkdir()
        (self.root / 'Documents/keep.txt').write_text('external', encoding='utf-8')
        with self.assertRaises(BrokerPolicyViolation): self.execute(review)
        self.assertEqual((self.root / 'Documents/keep.txt').read_text(encoding='utf-8'), 'external')
        self.assertTrue((self.root / 'note.txt').exists())

    def test_changed_source_rolls_back_created_bucket(self):
        (self.root / 'note.txt').write_text('source', encoding='utf-8')
        review = self.service.prepare('Files: organize fixture')
        (self.root / 'note.txt').write_text('external edit', encoding='utf-8')
        with self.assertRaises(BrokerPolicyViolation): self.execute(review)
        self.assertFalse((self.root / 'Documents').exists())
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), 'external edit')

    def test_undo_does_not_overwrite_later_edits_and_recovery_blocks_new_work(self):
        self.execute(self.service.prepare('Files: create fixture "note.txt" : original'))
        (self.root / 'note.txt').write_text('external', encoding='utf-8')
        with self.assertRaises(BrokerPolicyViolation): self.execute(self.service.prepare('Files: undo last'))
        self.assertTrue(self.state.incomplete_operations())
        with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: mkdir fixture "Blocked"')
        result = self.execute(self.service.prepare('Files: recover'))
        self.assertEqual(result['state'], 'RECOVERY REQUIRED')
        self.assertEqual((self.root / 'note.txt').read_text(encoding='utf-8'), 'external')

    def test_source_path_escape_and_unknown_root_rejected(self):
        for command in ['Files: mkdir fixture "../escape"', 'Files: mkdir unknown "folder"',
                        'Files: move fixture "missing.txt" to fixture "../escape"']:
            with self.subTest(command=command), self.assertRaises(BrokerPolicyViolation): self.service.prepare(command)

    def test_organization_ignores_nested_and_unknown_files(self):
        (self.root / 'Subfolder').mkdir()
        (self.root / 'Subfolder/keep.txt').write_text('keep', encoding='utf-8')
        (self.root / 'program.exe').write_bytes(b'keep')
        result = self.service.prepare('Files: organize fixture')
        self.assertEqual(result['type'], 'result')
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_organize_size_and_action_limits(self):
        large = self.root / 'large.txt'
        with large.open('wb') as stream: stream.truncate(16 * 1024 * 1024 + 1)
        with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: organize fixture')
        large.unlink()
        for i in range(50): (self.root / (str(i) + '.txt')).write_bytes(b'x')
        with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: organize fixture')
        self.assertFalse((self.root / 'Documents').exists())

    def test_folder_permission_needs_review_and_revalidates(self):
        new = self.base / 'Second Fixture'; new.mkdir()
        review = self.service.prepare('Files: add folder', str(new))
        self.assertEqual(len(self.store.load()), 1)
        self.execute(review)
        self.assertEqual(len(self.store.load()), 2)
        with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: add folder', str(new))

    def test_help_listing_and_metadata_status(self):
        self.assertIn('Files: organize', self.service.prepare('Files: help')['text'])
        self.assertIn('fixture', self.service.prepare('Files: folders')['text'])
        self.assertEqual(self.service.prepare('Files: list fixture')['state'], 'COMPLETED')
        self.execute(self.service.prepare('Files: create fixture "secret.txt" : secret content'))
        status = self.service.prepare('Files: status')['text']
        self.assertIn('undo: available', status)
        self.assertNotIn('secret content', status)
        self.assertIn('Completed', status)
        self.assertIn('1 create text', status)
        self.execute(self.service.prepare('Files: undo last'))
        reversed_status = self.service.prepare('Files: status')['text']
        self.assertIn('Undone', reversed_status)
        self.assertIn('Reversed steps: 1', reversed_status)
        self.assertIn('undo: unavailable', reversed_status)
        self.assertNotIn('secret.txt', reversed_status)

    def test_live_protocol_approval_and_terminal_exit(self):
        class Pipe:
            def __init__(self): self.lines = queue.Queue()
            def readline(self, limit): return self.lines.get(timeout=5)
        reader = Pipe()
        nonce = 'a' * 32
        reader.lines.put(json.dumps({'input': 'Files: mkdir fixture "Folder"', 'nonce': nonce}) + '\n')
        output = []
        class Writer:
            def write(_, line):
                value = json.loads(line); output.append(value)
                if value['type'] == 'review':
                    self.assertFalse((self.root / 'Folder').exists())
                    reader.lines.put(json.dumps({'command': 'approve', 'fingerprint': value['fingerprint'], 'nonce': nonce}) + '\n')
            def flush(_): pass
        self.assertEqual(serve(reader, Writer(), lambda: self.service), 0)
        reader.lines.put('')
        self.assertEqual(output[-1]['state'], 'COMPLETED')
        self.assertTrue((self.root / 'Folder').is_dir())
        self.assertTrue(all(v['nonce'] == nonce for v in output))

    def test_malformed_envelope_fails_before_service(self):
        for value in [{'input':'Files: help', 'nonce':'wrong'}, {'input':'Files: help', 'nonce':'a'*32, 'extra':True}]:
            with self.assertRaises(ValueError):
                serve(io.StringIO(json.dumps(value) + '\n'), io.StringIO(), lambda: self.fail('service invoked'))

    def test_remove_permission_is_reviewed_and_never_deletes_files(self):
        (self.root / 'keep.txt').write_bytes(b'keep')
        review = self.service.prepare('Files: remove fixture')
        self.assertEqual(len(self.store.load()), 1)
        self.execute(review)
        self.assertEqual(self.store.load(), [])
        self.assertEqual((self.root / 'keep.txt').read_bytes(), b'keep')

    def test_nested_execution_is_rejected_by_shared_lease(self):
        first = self.service.prepare('Files: mkdir fixture "First"')
        second = self.service.prepare('Files: mkdir fixture "Second"')
        other = self.service.operator()
        self.state.approve(second['id'], second['fingerprint'])
        def competing_operation(*args):
            with self.assertRaisesRegex(BrokerPolicyViolation, 'Another file operation is active'):
                other.apply(second['id'])
        self.execute(first, progress=competing_operation)
        self.assertFalse((self.root / 'Second').exists())
        other.apply(second['id'])
        self.assertTrue((self.root / 'Second').is_dir())

    def test_expired_native_review_retires_plan(self):
        class Pipe:
            def __init__(self): self.lines = queue.Queue()
            def readline(self, limit): return self.lines.get(timeout=3)
        reader = Pipe(); nonce = 'a' * 32
        reader.lines.put(json.dumps({'input': 'Files: mkdir fixture "Folder"', 'nonce': nonce}) + '\n')
        writer = io.StringIO()
        from local_assistant import file_tasks
        with patch.object(file_tasks, 'REVIEW_SECONDS', 0.01):
            serve(reader, writer, lambda: self.service)
        reader.lines.put('')
        self.assertEqual(json.loads(writer.getvalue().splitlines()[-1])['state'], 'CANCELLED')
        self.assertEqual(self.state.list_plans()[0].status, 'denied')
        self.assertFalse((self.root / 'Folder').exists())

    def test_reparse_entry_rejected_before_plan(self):
        (self.root / 'note.txt').write_bytes(b'fixture')
        with patch('local_assistant.file_tasks.ReadOnlyCapabilityBroker._is_reparse_point', return_value=True):
            with self.assertRaises(BrokerPolicyViolation): self.service.prepare('Files: organize fixture')
        self.assertFalse((self.root / 'Documents').exists())

    def test_stop_during_undo_preserves_remainder_for_reviewed_recovery(self):
        (self.root / 'note.txt').write_bytes(b'note')
        (self.root / 'budget.csv').write_bytes(b'budget')
        self.execute(self.service.prepare('Files: organize fixture'))
        undo = self.service.prepare('Files: undo last')
        op = self.service.operator()
        reverse = op._undo
        stop = threading.Event()
        def one_reverse(payload):
            reverse(payload); stop.set()
        with patch.object(self.service, 'operator', return_value=op), patch.object(op, '_undo', side_effect=one_reverse):
            with self.assertRaises(BrokerPolicyViolation): self.execute(undo, stopped=stop.is_set)
        self.assertTrue(self.state.incomplete_operations())
        self.execute(self.service.prepare('Files: recover'))
        self.assertFalse(self.state.incomplete_operations())
        self.assertEqual({p.name: p.read_bytes() for p in self.root.iterdir()}, {'note.txt': b'note', 'budget.csv': b'budget'})


if __name__ == '__main__': unittest.main()
