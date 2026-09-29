from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from local_assistant.broker_mcp import McpApplication
from local_assistant.capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker
from local_assistant.inventory_broker import InventoryRoot, MetadataInventoryBroker
from local_assistant.organization_planner import (
    DryRunOrganizationPlanner,
    MAX_PLAN_ITEMS,
    MAX_PROPOSALS_PER_TEN_MINUTES,
    OrganizationPlanStore,
)


class DryRunOrganizationPlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.sandbox = self.base / "Hermes Sandbox"
        self.source = self.base / "Approved Source"
        self.destination = self.base / "Approved Destination"
        self.sandbox.mkdir()
        self.source.mkdir()
        self.destination.mkdir()
        added = "2026-08-17T00:00:00+00:00"
        self.source_record = InventoryRoot("source", self.source.resolve(), added)
        self.destination_record = InventoryRoot(
            "graphic", self.destination.resolve(), added
        )
        self.audit = self.base / "audit.jsonl"
        self.inventory = MetadataInventoryBroker([self.source_record], self.audit)
        self.state = OrganizationPlanStore(self.base / "organization.db")
        self.planner = DryRunOrganizationPlanner(
            self.inventory, [self.destination_record], self.state, self.audit
        )
        (self.source / "poster.psd").write_bytes(b"private-psd-content")
        (self.source / "logo.svg").write_text(
            "<svg>private-vector-content</svg>", encoding="utf-8"
        )
        (self.source / "notes.txt").write_text("private notes", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _item(source: str, destination: str, reason: str = "Graphic extension"):
        return {
            "source_relative_path": source,
            "destination_relative_path": destination,
            "reason": reason,
        }

    def _propose_one(self) -> dict[str, object]:
        return self.planner.propose_graphic_plan(
            "source",
            "graphic",
            [self._item("poster.psd", "Design Sources/poster.psd")],
        )

    def test_status_is_explicitly_dry_run_only(self):
        result = self.planner.status()
        self.assertEqual(result["mode"], "dry-run-only")
        self.assertFalse(result["execution_available"])
        self.assertFalse(result["real_file_writes"])
        self.assertFalse(result["content_reads"])
        self.assertTrue(result["local_plan_state_writes"])
        self.assertEqual(result["limits"]["max_items_per_plan"], MAX_PLAN_ITEMS)

    def test_valid_plan_is_persisted_without_moving_or_creating_anything(self):
        before = (self.source / "poster.psd").stat()
        result = self._propose_one()
        self.assertEqual(result["status"], "proposed")
        self.assertFalse(result["execution_available"])
        self.assertEqual(result["item_count"], 1)
        self.assertTrue((self.source / "poster.psd").exists())
        self.assertFalse((self.destination / "Design Sources").exists())
        after = (self.source / "poster.psd").stat()
        self.assertEqual((before.st_size, before.st_mtime_ns), (after.st_size, after.st_mtime_ns))
        stored = self.state.get(result["plan_id"])
        self.assertEqual(stored.items[0]["source_relative_path"], "poster.psd")
        self.assertEqual(
            stored.items[0]["destination_relative_path"],
            "Design Sources/poster.psd",
        )

    def test_plan_and_validation_never_read_source_contents(self):
        with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("content read")), mock.patch.object(
            Path, "read_text", side_effect=AssertionError("content read")
        ):
            result = self._propose_one()
            validation = self.planner.validate_plan(result["plan_id"])
        self.assertTrue(validation["ready_for_human_review"])
        self.assertFalse(validation["content_read"])
        self.assertFalse(validation["real_files_changed"])

    def test_rejects_non_graphic_rename_traversal_absolute_and_reserved_targets(self):
        (self.source / "unsafe\u202ename.psd").write_bytes(b"unsafe")
        cases = (
            self._item("notes.txt", "Notes/notes.txt"),
            self._item("poster.psd", "Design Sources/renamed.psd"),
            self._item("poster.psd", "../poster.psd"),
            self._item("poster.psd", "C:\\Temp\\poster.psd"),
            self._item("poster.psd", "CON/poster.psd"),
            self._item("poster.psd", ".hidden/poster.psd"),
            self._item("poster.psd", "Safe\u202egnp.retsop/poster.psd"),
            self._item("unsafe\u202ename.psd", "Safe/unsafe-name.psd"),
        )
        for item in cases:
            with self.subTest(item=item), self.assertRaises(BrokerPolicyViolation):
                self.planner.propose_graphic_plan("source", "graphic", [item])

        with self.assertRaises(BrokerPolicyViolation):
            self.planner.propose_graphic_plan(
                "source",
                "graphic",
                [
                    self._item(
                        "poster.psd",
                        "Safe/poster.psd",
                        "Looks safe\u202ebut is misleading",
                    )
                ],
            )

    def test_rejects_duplicate_sources_destinations_and_existing_destination(self):
        duplicate_source = [
            self._item("poster.psd", "A/poster.psd"),
            self._item("poster.psd", "B/poster.psd"),
        ]
        with self.assertRaises(BrokerPolicyViolation):
            self.planner.propose_graphic_plan("source", "graphic", duplicate_source)

        (self.source / "Second").mkdir()
        (self.source / "Second" / "poster.psd").write_bytes(b"second")
        duplicate_destination = [
            self._item("poster.psd", "A/poster.psd"),
            self._item("Second/poster.psd", "A/poster.psd"),
        ]
        with self.assertRaises(BrokerPolicyViolation):
            self.planner.propose_graphic_plan(
                "source", "graphic", duplicate_destination
            )

        (self.destination / "poster.psd").write_bytes(b"existing")
        with self.assertRaises(BrokerPolicyViolation):
            self.planner.propose_graphic_plan(
                "source", "graphic", [self._item("poster.psd", "poster.psd")]
            )

    def test_rejects_unsafe_root_relationships_and_source_already_in_destination(self):
        same_destination = InventoryRoot(
            "same", self.source.resolve(), "2026-08-17T00:00:00+00:00"
        )
        same_planner = DryRunOrganizationPlanner(
            self.inventory, [same_destination], self.state, None
        )
        with self.assertRaises(BrokerPolicyViolation):
            same_planner.propose_graphic_plan(
                "source", "same", [self._item("poster.psd", "poster.psd")]
            )

        parent_destination = InventoryRoot(
            "parent", self.base.resolve(), "2026-08-17T00:00:00+00:00"
        )
        parent_planner = DryRunOrganizationPlanner(
            self.inventory, [parent_destination], self.state, None
        )
        with self.assertRaises(BrokerPolicyViolation):
            parent_planner.propose_graphic_plan(
                "source", "parent", [self._item("poster.psd", "poster.psd")]
            )

        nested_destination_path = self.source / "Graphic"
        nested_destination_path.mkdir()
        nested_file = nested_destination_path / "inside.psd"
        nested_file.write_bytes(b"inside")
        nested_destination = InventoryRoot(
            "nested", nested_destination_path.resolve(), "2026-08-17T00:00:00+00:00"
        )
        nested_planner = DryRunOrganizationPlanner(
            self.inventory, [nested_destination], self.state, None
        )
        with self.assertRaises(BrokerPolicyViolation):
            nested_planner.propose_graphic_plan(
                "source",
                "nested",
                [self._item("Graphic/inside.psd", "inside.psd")],
            )

    def test_validation_detects_changed_source_and_new_destination(self):
        first = self._propose_one()
        source_path = self.source / "poster.psd"
        source_path.write_bytes(b"changed-private-content")
        changed = self.planner.validate_plan(first["plan_id"])
        self.assertFalse(changed["still_matches_metadata"])
        self.assertEqual(changed["issues"][0]["code"], "item_not_ready")

        second = self.planner.propose_graphic_plan(
            "source",
            "graphic",
            [self._item("logo.svg", "Vectors/logo.svg")],
        )
        (self.destination / "Vectors").mkdir()
        (self.destination / "Vectors" / "logo.svg").write_text(
            "collision", encoding="utf-8"
        )
        collision = self.planner.validate_plan(second["plan_id"])
        self.assertFalse(collision["still_matches_metadata"])
        self.assertIn("Destination appeared", collision["issues"][0]["message"])

    def test_review_marks_only_plan_state_and_wrong_fingerprint_fails(self):
        result = self._propose_one()
        plan = self.state.get(result["plan_id"])
        with self.assertRaises(BrokerPolicyViolation):
            self.state.mark_reviewed(plan.plan_id, "wrong")
        validation = self.planner.validate_plan(plan.plan_id)
        self.assertTrue(validation["ready_for_human_review"])
        reviewed = self.state.mark_reviewed(plan.plan_id, plan.fingerprint)
        self.assertEqual(reviewed.status, "reviewed")
        self.assertTrue((self.source / "poster.psd").exists())
        self.assertFalse((self.destination / "Design Sources").exists())

    def test_tampered_stored_plan_is_rejected_by_fingerprint_check(self):
        result = self._propose_one()
        with self.state._managed_connection() as connection:
            connection.execute(
                "UPDATE organization_plans SET items_json=? WHERE plan_id=?",
                ('[{"source_relative_path":"tampered.psd"}]', result["plan_id"]),
            )
        with self.assertRaises(BrokerPolicyViolation):
            self.state.get(result["plan_id"])

    def test_expired_plan_is_marked_and_cannot_be_reviewed(self):
        result = self._propose_one()
        original = self.state.get(result["plan_id"])
        future = datetime.fromisoformat(original.expires_at) + timedelta(minutes=1)
        with mock.patch(
            "local_assistant.organization_planner.utc_now", return_value=future
        ):
            validation = self.planner.validate_plan(result["plan_id"])
        self.assertEqual(validation["status"], "expired")
        self.assertFalse(validation["ready_for_human_review"])
        plan = self.state.get(result["plan_id"])
        with self.assertRaises(BrokerPolicyViolation):
            self.state.mark_reviewed(plan.plan_id, plan.fingerprint)

    def test_audit_has_plan_metadata_but_no_filenames_reasons_or_contents(self):
        private_reason = "private client campaign asset"
        result = self.planner.propose_graphic_plan(
            "source",
            "graphic",
            [self._item("poster.psd", "Private/poster.psd", private_reason)],
        )
        self.planner.get_plan(result["plan_id"])
        self.planner.validate_plan(result["plan_id"])
        audit_text = self.audit.read_text(encoding="utf-8")
        self.assertIn(result["plan_id"], audit_text)
        for private_value in (
            "poster.psd",
            "Private/poster.psd",
            private_reason,
            "private-psd-content",
        ):
            self.assertNotIn(private_value, audit_text)

    def test_mcp_retains_dry_run_organization_tools_alongside_operator_tools(self):
        sandbox = ReadOnlyCapabilityBroker(self.sandbox, self.audit)
        app = McpApplication(
            sandbox, inventory=self.inventory, organization=self.planner
        )
        listed = app.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertEqual(len(names), 22)
        self.assertIn("organization_propose_graphic_plan", names)
        self.assertIn("organization_validate_plan", names)
        self.assertNotIn("organization_apply_plan", names)
        self.assertNotIn("organization_move", names)
        self.assertNotIn("organization_delete", names)

        rejected = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "organization_status",
                    "arguments": {"execute": True},
                },
            }
        )
        self.assertTrue(rejected["result"]["isError"])

    def test_proposal_rate_limit_stops_plan_database_flooding(self):
        for _ in range(MAX_PROPOSALS_PER_TEN_MINUTES):
            self._propose_one()
        with self.assertRaises(BrokerPolicyViolation):
            self._propose_one()


if __name__ == "__main__":
    unittest.main()
