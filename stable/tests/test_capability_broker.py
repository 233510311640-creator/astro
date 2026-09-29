from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from local_assistant.broker_mcp import McpApplication
from local_assistant.capability_broker import (
    BrokerLimits,
    BrokerPolicyViolation,
    ReadOnlyCapabilityBroker,
)


class CapabilityBrokerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "Hermes Sandbox"
        self.root.mkdir()
        self.audit = self.base / "data" / "audit.jsonl"
        self.broker = ReadOnlyCapabilityBroker(
            self.root, self.audit, BrokerLimits(max_list_entries=10, max_read_bytes=100)
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_status_is_read_only(self):
        result = self.broker.status()
        self.assertEqual(result["mode"], "read-only")
        self.assertFalse(result["write_operations"])

    def test_lists_only_visible_non_link_entries(self):
        (self.root / "notes.txt").write_text("hello", encoding="utf-8")
        (self.root / ".env").write_text("SECRET=x", encoding="utf-8")
        result = self.broker.list_directory(".")
        self.assertEqual([entry["name"] for entry in result["entries"]], ["notes.txt"])
        self.assertEqual(result["skipped_protected"], 1)

    def test_rejects_traversal_absolute_and_drive_paths(self):
        for value in (
            "../outside.txt",
            str(self.base / "outside.txt"),
            "C:\\Windows",
            "\\\\?\\C:\\Windows\\System32",
        ):
            with self.subTest(value=value), self.assertRaises(BrokerPolicyViolation):
                self.broker.resolve(value)

    def test_rejects_windows_aliases_devices_and_alternate_streams(self):
        for value in (
            "note.txt:secret",
            "CON",
            "con.txt",
            "NUL.json",
            "COM1.log",
            "LPT9.txt",
            "SECRET~1.TXT",
            "report.txt.",
            "folder ",
        ):
            with self.subTest(value=value), self.assertRaises(BrokerPolicyViolation):
                self.broker.resolve_new_target(value)

    def test_reparse_components_are_rejected_before_resolution(self):
        (self.root / "junction").mkdir()
        original = self.broker._is_reparse_point
        try:
            self.broker._is_reparse_point = lambda path: path.name == "junction"
            with self.assertRaises(BrokerPolicyViolation):
                self.broker.resolve("junction", require_dir=True)
        finally:
            self.broker._is_reparse_point = original

    def test_rejects_symlink_escape(self):
        outside = self.base / "outside"
        outside.mkdir()
        link = self.root / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks are not available on this platform")
        with self.assertRaises(BrokerPolicyViolation):
            self.broker.resolve("link", require_dir=True)

    def test_reads_small_utf8_text(self):
        (self.root / "task.md").write_text("safe task", encoding="utf-8")
        result = self.broker.read_text("task.md")
        self.assertEqual(result["content"], "safe task")

    def test_rejects_binary_protected_and_large_files(self):
        (self.root / "image.png").write_bytes(b"png")
        (self.root / "auth.json").write_text("{}", encoding="utf-8")
        (self.root / "large.txt").write_text("x" * 101, encoding="utf-8")
        for value in ("image.png", "auth.json", "large.txt"):
            with self.subTest(value=value), self.assertRaises(BrokerPolicyViolation):
                self.broker.read_text(value, max_bytes=100)

    def test_audit_log_contains_metadata_not_content(self):
        secret_content = "not-for-the-log"
        (self.root / "note.txt").write_text(secret_content, encoding="utf-8")
        self.broker.read_text("note.txt")
        audit_text = self.audit.read_text(encoding="utf-8")
        self.assertNotIn(secret_content, audit_text)
        record = json.loads(audit_text.splitlines()[-1])
        self.assertEqual(record["tool"], "sandbox_read_text")

    def test_mcp_lists_only_expected_tools_and_rejects_unknown(self):
        app = McpApplication(self.broker)
        listed = app.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        self.assertEqual(len(listed["result"]["tools"]), 22)
        called = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "delete_everything", "arguments": {}},
            }
        )
        self.assertTrue(called["result"]["isError"])

    def test_mcp_rejects_unexpected_and_wrong_type_arguments(self):
        app = McpApplication(self.broker)
        cases = (
            {"name": "sandbox_status", "arguments": {"write": True}},
            {"name": "sandbox_list", "arguments": {"max_entries": True}},
            {"name": "sandbox_read_text", "arguments": {"relative_path": ["note.txt"]}},
        )
        for index, params in enumerate(cases, start=1):
            with self.subTest(params=params):
                called = app.dispatch(
                    {"jsonrpc": "2.0", "id": index, "method": "tools/call", "params": params}
                )
                self.assertTrue(called["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
