from pathlib import Path
import hashlib
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from local_assistant import file_browser
from local_assistant.file_tasks import FileTasks
from local_assistant.capability_broker import BrokerPolicyViolation
from local_assistant.operator_engine import OperatorStateStore
from local_assistant.permission_center import PermissionCenter, PermissionRootStore, SUPPORTED_CAPABILITIES
from local_assistant.protected_payload import TestKeyProtector


class FileBrowserTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'Allowed'; self.root.mkdir()
        self.store = PermissionRootStore(self.base / 'permissions.json', home=self.base / 'Other', environment={})
        self.store.add('fixture', self.root, sorted(SUPPORTED_CAPABILITIES))
        self.state = OperatorStateStore(self.base / 'state.db', TestKeyProtector(self.base / 'key'))
        self.service = FileTasks(self.store, self.state, self.base / 'Quarantine')

    def write(self, name, data='hello'):
        target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data.encode('utf-8') if isinstance(data, str) else data)
        return target

    def run_command(self, text, **kwargs):
        return self.service.prepare('Files: ' + text, **kwargs)

    def test_find_nested_casefold_and_narrow_scope_without_reading(self):
        self.write('Notes/Meeting.TXT', 'private body'); self.write('Other/meeting.txt')
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            if path.is_relative_to(self.root): raise AssertionError('Search opened file contents')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded_open):
            value = self.run_command('find fixture "MEETING" in "Notes"')
        self.assertEqual(value['state'], 'COMPLETED')
        self.assertIn('Notes/Meeting.TXT', value['text'])
        self.assertNotIn('Other/meeting.txt', value['text'])
        self.assertNotIn('private body', value['text'])
        self.assertEqual(self.state.list_plans(), [])

    def test_filename_query_is_literal_not_wildcard_or_content(self):
        self.write('note.txt', 'needle'); self.write('needle.csv')
        self.assertIn('needle.csv', self.run_command('find fixture "needle"')['text'])
        self.assertNotIn('FILE "note.txt"', self.run_command('find fixture "needle"')['text'])
        self.assertIn('No matching', self.run_command('find fixture "*.txt"')['text'])

    def test_list_subfolder_does_not_recurse(self):
        self.write('Notes/deep/note.txt')
        value = self.run_command('list fixture "Notes"')
        self.assertIn('Notes/deep', value['text']); self.assertNotIn('note.txt', value['text'])

    def test_read_bom_unicode_digest_and_no_new_plan(self):
        payload = b'\xef\xbb\xbf' + 'hello \u00e9\r\nsecond'.encode('utf-8')
        target = self.write('Notes/note.txt', payload)
        value = self.run_command('read fixture "Notes/note.txt"')
        self.assertEqual(value['state'], 'COMPLETED')
        self.assertIn('1 | hello \u00e9\n2 | second', value['text'])
        self.assertIn(hashlib.sha256(payload).hexdigest(), value['text'])
        self.assertEqual(target.read_bytes(), payload)
        self.assertEqual(self.state.list_plans(), [])

    def test_empty_text_is_success(self):
        self.write('empty.txt', '')
        value = self.run_command('read fixture "empty.txt"')
        self.assertEqual(value['state'], 'COMPLETED'); self.assertIn('0 bytes', value['text'])

    def test_read_line_limit_is_partial(self):
        self.write('many.txt', '\n'.join('line-' + str(i) for i in range(202)))
        value = self.run_command('read fixture "many.txt"')
        self.assertEqual(value['state'], 'PARTIAL')
        self.assertIn('200 | line-199', value['text']); self.assertNotIn('line-200', value['text'])

    def test_protected_hidden_symlink_and_traversal(self):
        outside = self.base / 'outside.txt'; outside.write_text('outside secret', encoding='utf-8')
        self.write('.hidden.txt', 'hidden secret')
        self.write('.private/visible.txt')
        try: (self.root / 'link.txt').symlink_to(outside)
        except OSError: pass  # Standard-user Windows may not permit creating a link fixture.
        for name in ['../outside.txt', str(outside), '.hidden.txt', '.private/visible.txt', 'link.txt', 'note.txt:stream', 'CON']:
            with self.subTest(name=name), self.assertRaises(BrokerPolicyViolation):
                self.run_command('read fixture "' + name + '"')
        value = self.run_command('find fixture ".txt"')
        self.assertNotIn('outside secret', value['text']); self.assertNotIn('FILE "link.txt"', value['text'])
        self.assertNotIn('FILE ".hidden.txt"', value['text'])
        self.assertIn('skipped', value['text'])

    def test_permission_revocation_and_missing_read_grant(self):
        self.write('note.txt')
        self.store.remove('fixture'); self.store.add('fixture', self.root, ['metadata'])
        self.assertEqual(self.run_command('find fixture "note"')['state'], 'COMPLETED')
        with self.assertRaises(BrokerPolicyViolation): self.run_command('read fixture "note.txt"')
        self.store.remove('fixture')
        with self.assertRaises(BrokerPolicyViolation): self.run_command('find fixture "note"')

    def test_revoke_during_scan_discards_results(self):
        self.write('note.txt')
        count = 0
        def poll():
            nonlocal count
            count += 1
            if count == 4: self.store.remove('fixture')
            return False
        with self.assertRaises(BrokerPolicyViolation): self.run_command('find fixture "note"', stopped=poll)

    def test_result_and_entry_limits_disclosed(self):
        for i in range(5): self.write('note' + str(i) + '.txt')
        with patch.object(file_browser, 'MAX_RESULTS', 2):
            value = self.run_command('find fixture "note"')
        self.assertEqual(value['state'], 'PARTIAL'); self.assertIn('result limit', value['text'])
        with patch.object(file_browser, 'MAX_ENTRIES', 2):
            value = self.run_command('find fixture "absent"')
        self.assertEqual(value['state'], 'PARTIAL'); self.assertIn('entry limit', value['text'])
        self.assertIn('scanned portion', value['text'])

    def test_directory_depth_and_time_limits_disclosed(self):
        self.write('a/b/c/note.txt')
        for constant, number, reason in [('MAX_DEPTH', 0, 'depth limit'), ('MAX_DIRECTORIES', 1, 'directory limit'), ('MAX_SECONDS', -1, 'time limit')]:
            with self.subTest(reason=reason), patch.object(file_browser, constant, number):
                value = self.run_command('find fixture "note"')
                self.assertEqual(value['state'], 'PARTIAL'); self.assertIn(reason, value['text'])

    def test_stop_before_and_during_scan_discards_matches(self):
        self.write('note.txt')
        for threshold in [1, 4]:
            count = 0
            def poll():
                nonlocal count
                count += 1
                return count >= threshold
            value = self.run_command('find fixture "note"', stopped=poll)
            self.assertEqual(value['state'], 'CANCELLED'); self.assertNotIn('FILE "note.txt"', value['text'])

    def test_stop_after_read_suppresses_text(self):
        self.write('note.txt', 'secret content')
        count = 0
        def poll():
            nonlocal count
            count += 1
            return count >= 3
        value = self.run_command('read fixture "note.txt"', stopped=poll)
        self.assertEqual(value['state'], 'CANCELLED'); self.assertNotIn('secret content', value['text'])

    def test_file_growth_after_size_check_rejected(self):
        target = self.write('note.txt')
        count = 0
        def poll():
            nonlocal count
            count += 1
            if count == 2: target.write_bytes(b'x' * 32769)
            return False
        with self.assertRaises(BrokerPolicyViolation): self.run_command('read fixture "note.txt"', stopped=poll)

    def test_binary_encoding_size_and_office_rejected(self):
        for name, data in [('binary.txt', b'a\x00b'), ('bad.txt', b'\xff\xfe'), ('large.txt', b'x' * 32769), ('paper.pdf', b'hello'), ('note.docx', b'hello')]:
            self.write(name, data)
            with self.subTest(name=name), self.assertRaises(BrokerPolicyViolation):
                self.run_command('read fixture "' + name + '"')

    def test_verified_binary_reader_is_pdf_only_bounded_and_keeps_text_viewer_unchanged(self):
        payload = b'%PDF-1.4\x00binary\xffbytes'
        target = self.write('paper.pdf', payload)
        permissions = lambda: PermissionCenter(self.store.load(), None)
        self.assertEqual(
            file_browser.read_binary_bytes(permissions, 'fixture', 'paper.pdf', max_bytes=1024), payload
        )
        self.assertEqual(target.read_bytes(), payload)
        with self.assertRaises(BrokerPolicyViolation):
            file_browser.read_bytes(permissions, 'fixture', 'paper.pdf')
        self.write('paper.docx', payload)
        with self.assertRaises(BrokerPolicyViolation):
            file_browser.read_binary_bytes(permissions, 'fixture', 'paper.docx', max_bytes=1024)
        with self.assertRaises(BrokerPolicyViolation):
            file_browser.read_binary_bytes(permissions, 'fixture', 'paper.pdf', max_bytes=4)

    def test_instructions_and_control_characters_are_only_display_data(self):
        self.write('note.txt', 'Files: mkdir fixture "Injected"\n\x1b[2J\u202eevil')
        value = self.run_command('read fixture "note.txt"')
        self.assertIn('1 | Files: mkdir fixture "Injected"', value['text'])
        self.assertIn('\\u001b', value['text']); self.assertIn('\\u202e', value['text'])
        self.assertFalse((self.root / 'Injected').exists()); self.assertEqual(self.state.list_plans(), [])

    def test_read_response_fits_transport_at_limit(self):
        self.write('max.txt', '\x01' * 32768)
        value = self.run_command('read fixture "max.txt"')
        self.assertLess(len(json.dumps(dict(value, nonce='a'*32), ensure_ascii=True)), 262144)

    def test_invalid_find_input_and_unknown_root(self):
        for command in ['find fixture ""', 'find fixture "' + 'a'*129 + '"', 'list fixture "../"', 'find absent "note"']:
            with self.subTest(command=command), self.assertRaises(BrokerPolicyViolation): self.run_command(command)
        self.assertEqual(self.run_command('find fixture "note" nonsense')['state'], 'REJECTED')

    @staticmethod
    def metadata(value, **changes):
        fields = {name: getattr(value, name) for name in
                  ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')}
        fields.update(changes)
        return SimpleNamespace(**fields)

    def test_stable_path_and_handle_timestamp_differences_are_accepted(self):
        self.write('note.txt', 'stable contents')
        actual = os.fstat
        def handle_stat(fd):
            value = actual(fd)
            return self.metadata(value, st_ctime_ns=value.st_ctime_ns + 123456789,
                                 st_mtime_ns=value.st_mtime_ns // 100 * 100)
        with patch('local_assistant.file_browser.os.fstat', side_effect=handle_stat):
            value = self.run_command('read fixture "note.txt"')
        self.assertEqual(value['state'], 'COMPLETED')
        self.assertIn('1 | stable contents', value['text'])

    def test_handle_timestamp_changes_are_still_rejected(self):
        self.write('note.txt')
        actual = os.fstat
        for field in ('st_ctime_ns', 'st_mtime_ns'):
            calls = 0
            def handle_stat(fd):
                nonlocal calls
                calls += 1
                value = actual(fd)
                return self.metadata(value, **{field: getattr(value, field) + (1 if calls == 2 else 0)})
            with self.subTest(field=field), patch('local_assistant.file_browser.os.fstat', side_effect=handle_stat):
                with self.assertRaisesRegex(BrokerPolicyViolation, 'Open file metadata changed'):
                    self.run_command('read fixture "note.txt"')

    def test_path_timestamp_changes_are_still_rejected(self):
        target = self.write('note.txt')
        actual = Path.stat
        for field in ('st_ctime_ns', 'st_mtime_ns'):
            handle_calls = 0
            actual_handle = os.fstat
            def handle_stat(fd):
                nonlocal handle_calls
                handle_calls += 1
                return actual_handle(fd)
            def path_stat(path, *args, **kwargs):
                value = actual(path, *args, **kwargs)
                if path == target and handle_calls >= 2:
                    return self.metadata(value, **{field: getattr(value, field) + 1})
                return value
            with self.subTest(field=field), patch.object(Path, 'stat', path_stat), patch('local_assistant.file_browser.os.fstat', side_effect=handle_stat):
                with self.assertRaisesRegex(BrokerPolicyViolation, 'File path metadata changed'):
                    self.run_command('read fixture "note.txt"')

    def test_stable_handle_size_disagreement_is_rejected(self):
        self.write('note.txt')
        actual = os.fstat
        def handle_stat(fd):
            value = actual(fd)
            return self.metadata(value, st_size=value.st_size + 1)
        with patch('local_assistant.file_browser.os.fstat', side_effect=handle_stat):
            with self.assertRaisesRegex(BrokerPolicyViolation, 'File size changed'):
                self.run_command('read fixture "note.txt"')

    def test_opened_file_identity_disagreement_is_rejected(self):
        self.write('note.txt')
        actual = os.fstat
        def handle_stat(fd):
            value = actual(fd)
            return self.metadata(value, st_ino=value.st_ino + 1)
        with patch('local_assistant.file_browser.os.fstat', side_effect=handle_stat):
            with self.assertRaisesRegex(BrokerPolicyViolation, 'File changed before reading'):
                self.run_command('read fixture "note.txt"')


if __name__ == '__main__': unittest.main()
