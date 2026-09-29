from __future__ import annotations

import json
from pathlib import Path
from unittest import mock
import tempfile
import unittest

from local_assistant.broker_mcp import McpApplication
from local_assistant.capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker
from local_assistant.inventory_broker import (
    InventoryLimits,
    InventoryRoot,
    InventoryRootStore,
    MetadataInventoryBroker,
)


class InventoryRootStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.home = self.base / "User"
        self.home.mkdir()
        self.desktop = self.home / "Desktop"
        self.downloads = self.home / "Downloads"
        self.desktop.mkdir()
        self.downloads.mkdir()
        self.config = self.base / "data" / "inventory_roots.json"
        self.store = InventoryRootStore(self.config, home=self.home, environment={})

    def tearDown(self):
        self.temp.cleanup()

    def test_add_load_and_remove_root(self):
        added = self.store.add("desktop", self.desktop)
        self.assertEqual(added.path, self.desktop.resolve())
        loaded = self.store.load()
        self.assertEqual([(item.root_id, item.path) for item in loaded], [("desktop", added.path)])
        payload = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(set(payload), {"version", "roots"})
        self.store.remove("desktop")
        self.assertEqual(self.store.load(), [])

    def test_rejects_broad_protected_invalid_and_overlapping_roots(self):
        app_data = self.home / "AppData" / "Local"
        app_data.mkdir(parents=True)
        self.store.add("desktop", self.desktop)
        cases = (
            ("UserHome", self.downloads),
            ("users", self.base),
            ("home", self.home),
            ("appdata", app_data),
            ("nested", self.desktop / "Project"),
        )
        (self.desktop / "Project").mkdir()
        for root_id, path in cases:
            with self.subTest(root_id=root_id), self.assertRaises(BrokerPolicyViolation):
                self.store.add(root_id, path)

    def test_rejects_symlink_root_and_tampered_config(self):
        link = self.home / "Linked"
        try:
            link.symlink_to(self.downloads, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks are unavailable on this platform")
        with self.assertRaises(BrokerPolicyViolation):
            self.store.add("linked", link)

        self.config.parent.mkdir(parents=True, exist_ok=True)
        self.config.write_text('{"version":1,"roots":[],"unexpected":true}', encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.store.load()

        self.config.write_text(
            json.dumps(
                {
                    "version": 1,
                    "roots": [
                        {
                            "id": "downloads",
                            "path": str(self.downloads),
                            "added_at": "not-a-timestamp",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        with self.assertRaises(BrokerPolicyViolation):
            self.store.load()


class MetadataInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.sandbox = self.base / "Hermes Sandbox"
        self.inventory_root = self.base / "Approved Desktop"
        self.sandbox.mkdir()
        self.inventory_root.mkdir()
        self.audit = self.base / "audit.jsonl"
        self.root_record = InventoryRoot(
            "desktop", self.inventory_root.resolve(), "2026-08-17T00:00:00+00:00"
        )
        self.inventory = MetadataInventoryBroker([self.root_record], self.audit)

    def tearDown(self):
        self.temp.cleanup()

    def test_status_discloses_metadata_only_boundary(self):
        result = self.inventory.status()
        self.assertEqual(result["mode"], "metadata-only")
        self.assertFalse(result["content_reads"])
        self.assertFalse(result["write_operations"])
        self.assertEqual(result["roots"][0]["root_id"], "desktop")

    def test_lists_metadata_without_reading_contents(self):
        (self.inventory_root / "poster.psd").write_bytes(b"secret-layer-data")
        (self.inventory_root / "notes.txt").write_text("private notes", encoding="utf-8")
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("content read")), mock.patch.object(
            Path, "read_text", side_effect=AssertionError("content read")
        ):
            result = self.inventory.list_directory("desktop")
        self.assertEqual(
            [item["relative_path"] for item in result["entries"]],
            ["notes.txt", "poster.psd"],
        )
        self.assertTrue(all("content" not in item for item in result["entries"]))

    def test_graphic_candidates_are_extension_only_and_bounded(self):
        assets = self.inventory_root / "Assets"
        assets.mkdir()
        (assets / "brand.psd").write_bytes(b"psd-private")
        (assets / "logo.svg").write_text("<svg>private</svg>", encoding="utf-8")
        (assets / "photo.png").write_bytes(b"png-private")
        (assets / "brief.txt").write_text("private brief", encoding="utf-8")
        (assets / ".hidden.jpg").write_bytes(b"hidden")

        result = self.inventory.graphic_candidates(
            "desktop", "Assets", max_depth=0, max_results=20
        )
        paths = [item["relative_path"] for item in result["candidates"]]
        self.assertEqual(paths, ["Assets/brand.psd", "Assets/logo.svg", "Assets/photo.png"])
        self.assertEqual(
            [item["category"] for item in result["candidates"]],
            ["design_source", "vector_asset", "image_asset"],
        )
        self.assertFalse(result["content_read"])
        self.assertGreaterEqual(result["skipped_protected_or_unavailable"], 1)

    def test_summary_returns_counts_without_filenames(self):
        (self.inventory_root / "one.png").write_bytes(b"1")
        folder = self.inventory_root / "Nested"
        folder.mkdir()
        (folder / "two.psd").write_bytes(b"22")
        (folder / "three.txt").write_text("333", encoding="utf-8")
        result = self.inventory.summarize("desktop", max_depth=1)
        self.assertEqual(result["files_examined"], 3)
        self.assertEqual(result["extension_counts"], {".png": 1, ".psd": 1, ".txt": 1})
        self.assertEqual(result["graphic_category_counts"], {"design_source": 1, "image_asset": 1})
        rendered = json.dumps(result)
        self.assertNotIn("one.png", rendered)
        self.assertNotIn("two.psd", rendered)

    def test_rejects_unknown_root_traversal_and_invalid_limits(self):
        cases = (
            lambda: self.inventory.list_directory("unknown"),
            lambda: self.inventory.list_directory("desktop", "../outside"),
            lambda: self.inventory.list_directory("desktop", "..\\outside"),
            lambda: self.inventory.list_directory("desktop", "/outside"),
            lambda: self.inventory.list_directory("desktop", "C:\\Windows"),
            lambda: self.inventory.list_directory("desktop", "\\\\server\\share"),
            lambda: self.inventory.summarize("desktop", max_depth=9),
            lambda: self.inventory.graphic_candidates("desktop", max_results=0),
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(BrokerPolicyViolation):
                case()

    def test_symlink_entries_are_skipped(self):
        outside = self.base / "Outside"
        outside.mkdir()
        (outside / "secret.psd").write_bytes(b"secret")
        link = self.inventory_root / "Linked"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("Symlinks are unavailable on this platform")
        result = self.inventory.graphic_candidates("desktop", max_depth=3)
        self.assertEqual(result["candidates"], [])
        self.assertGreaterEqual(result["skipped_protected_or_unavailable"], 1)

    def test_scan_caps_are_enforced(self):
        for index in range(8):
            (self.inventory_root / f"asset-{index}.png").write_bytes(b"x")
        limited = MetadataInventoryBroker(
            [self.root_record],
            None,
            InventoryLimits(
                max_results=3,
                max_depth=1,
                max_items_examined=4,
                max_directories_examined=2,
                max_entries_per_directory=10,
            ),
        )
        result = limited.graphic_candidates("desktop", max_depth=1, max_results=3)
        self.assertEqual(result["returned"], 3)
        self.assertTrue(result["truncated"])

    def test_inventory_audit_never_records_scanned_or_rejected_filenames(self):
        private_name = "private-client-name.png"
        (self.inventory_root / private_name).write_bytes(b"private-content")
        self.inventory.list_directory("desktop")
        self.inventory.graphic_candidates("desktop")

        sandbox_broker = ReadOnlyCapabilityBroker(self.sandbox, self.audit)
        app = McpApplication(sandbox_broker, inventory=self.inventory)
        missing_name = "missing-private-name.png"
        rejected = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "inventory_list_directory",
                    "arguments": {
                        "root_id": "desktop",
                        "relative_directory": missing_name,
                    },
                },
            }
        )
        self.assertTrue(rejected["result"]["isError"])

        audit_text = self.audit.read_text(encoding="utf-8")
        self.assertNotIn(private_name, audit_text)
        self.assertNotIn(missing_name, audit_text)
        self.assertNotIn("private-content", audit_text)

    def test_mcp_exposes_only_expected_tools_and_strict_arguments(self):
        sandbox_broker = ReadOnlyCapabilityBroker(self.sandbox, None)
        app = McpApplication(sandbox_broker, inventory=self.inventory)
        listed = app.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "sandbox_status",
                "sandbox_list",
                "sandbox_read_text",
                "sandbox_propose_create_text",
                "sandbox_propose_replace_text",
                "sandbox_propose_make_directory",
                "sandbox_propose_move",
                "sandbox_apply_approved_plan",
                "inventory_status",
                "inventory_list_directory",
                "inventory_summarize",
                "inventory_graphic_candidates",
                "organization_status",
                "organization_propose_graphic_plan",
                "organization_get_plan",
                "organization_validate_plan",
                "operator_permission_status",
                "operator_read_text",
                "operator_propose_plan",
                "operator_get_plan",
                "operator_apply_approved_plan",
                "operator_operation_status",
            },
        )
        self.assertNotIn("inventory_read_file", names)
        self.assertNotIn("inventory_move", names)
        rejected = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "inventory_summarize",
                    "arguments": {"root_id": "desktop", "read_contents": True},
                },
            }
        )
        self.assertTrue(rejected["result"]["isError"])


if __name__ == "__main__":
    unittest.main()
