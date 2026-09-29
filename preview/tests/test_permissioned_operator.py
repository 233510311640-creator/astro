from __future__ import annotations

from contextlib import closing
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from local_assistant.capability_broker import BrokerPolicyViolation
from local_assistant.broker_mcp import McpApplication
from local_assistant.operator_engine import (
    OperatorStateStore,
    PermissionedOperator,
    utc_now,
)
from local_assistant.permission_center import PermissionCenter, PermissionRootStore
from local_assistant.protected_payload import PayloadProtectionError, TestKeyProtector


ALL_CAPABILITIES = [
    "metadata",
    "read_text",
    "create_text",
    "replace_text",
    "copy",
    "move",
    "rename",
    "mkdir",
    "quarantine",
]


class PermissionedOperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "Approved Source"
        self.destination = self.base / "Approved Destination"
        self.source.mkdir()
        self.destination.mkdir()
        self.permission_path = self.base / "operator_permissions.json"
        store = PermissionRootStore(
            self.permission_path,
            home=self.base / "Unrelated Home",
            environment={},
        )
        store.add("source", self.source, ALL_CAPABILITIES)
        store.add("destination", self.destination, ALL_CAPABILITIES)
        self.permissions = PermissionCenter(store.load(), self.base / "audit.jsonl")
        self.protector = TestKeyProtector(self.base / "test-protection.key")
        self.state = OperatorStateStore(self.base / "operator.db", self.protector)
        self.operator = PermissionedOperator(
            self.permissions, self.state, self.base / "Cypher Quarantine"
        )

    def tearDown(self):
        self.temp.cleanup()

    def approve(self, result: dict[str, object]) -> None:
        plan = self.state.get_plan(str(result["plan_id"]))
        self.state.approve(plan.plan_id, plan.fingerprint)

    @staticmethod
    def create_action(path: str, content: str = "hello") -> dict[str, object]:
        return {
            "kind": "create_text",
            "root_id": "destination",
            "relative_path": path,
            "content": content,
        }

    def test_permission_store_is_human_managed_scoped_and_atomic(self):
        payload = json.loads(self.permission_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 1)
        self.assertEqual(len(payload["roots"]), 2)
        self.assertIn("metadata", payload["roots"][0]["capabilities"])
        self.assertFalse(self.permissions.status()["ambient_access"])
        with self.assertRaises(BrokerPolicyViolation):
            PermissionRootStore(
                self.base / "other.json",
                home=self.base / "Unrelated Home",
                environment={},
            ).add("unsafe", self.base, ["metadata"])

    def test_permission_store_rejects_unknown_capability_overlap_and_tamper(self):
        store = PermissionRootStore(
            self.permission_path,
            home=self.base / "Unrelated Home",
            environment={},
        )
        nested = self.source / "Nested"
        nested.mkdir()
        with self.assertRaises(BrokerPolicyViolation):
            store.add("nested", nested, ["read_text"])
        with self.assertRaises(BrokerPolicyViolation):
            store.add("bad", self.base / "Missing", ["root_shell"])
        payload = json.loads(self.permission_path.read_text(encoding="utf-8"))
        payload["roots"][0]["capabilities"].append("root_shell")
        self.permission_path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            store.load()

    def test_direct_content_read_requires_scope_and_never_logs_content(self):
        (self.source / "notes.txt").write_text("private words", encoding="utf-8")
        result = self.permissions.read_text("source", "notes.txt")
        self.assertEqual(result["content"], "private words")
        audit = (self.base / "audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn("private words", audit)
        self.assertNotIn("notes.txt", audit)

    def test_proposal_is_encrypted_requires_approval_and_executes_once(self):
        result = self.operator.propose([self.create_action("created.txt", "secret payload")])
        self.assertFalse((self.destination / "created.txt").exists())
        database_bytes = self.state.path.read_bytes()
        self.assertNotIn(b"secret payload", database_bytes)
        self.assertNotIn(b"created.txt", database_bytes)
        human_review = self.operator.human_review_plan(str(result["plan_id"]))
        self.assertEqual(human_review["actions"][0]["content"], "secret payload")
        self.assertEqual(human_review["approval_code"], result["approval_code"])
        with self.assertRaises(BrokerPolicyViolation):
            self.operator.apply(str(result["plan_id"]))
        self.approve(result)
        applied = self.operator.apply(str(result["plan_id"]))
        self.assertEqual(
            (self.destination / "created.txt").read_text(encoding="utf-8"),
            "secret payload",
        )
        self.assertEqual(applied["verified_items"], 1)
        with self.assertRaises(BrokerPolicyViolation):
            self.operator.apply(str(result["plan_id"]))
        self.operator.undo_operation(str(applied["operation_id"]))
        self.assertFalse((self.destination / "created.txt").exists())

    def test_protected_plan_tamper_is_rejected(self):
        result = self.operator.propose([self.create_action("tamper.txt")])
        with closing(sqlite3.connect(self.state.path)) as connection:
            with connection:
                row = connection.execute(
                    "SELECT payload_protected FROM operator_plans WHERE plan_id=?",
                    (result["plan_id"],),
                ).fetchone()
                protected = row[0]
                replacement = protected[:-1] + ("A" if protected[-1] != "A" else "B")
                connection.execute(
                    "UPDATE operator_plans SET payload_protected=? WHERE plan_id=?",
                    (replacement, result["plan_id"]),
                )
        with self.assertRaises(BrokerPolicyViolation):
            self.state.get_plan(str(result["plan_id"]))

    def test_create_replace_copy_move_rename_mkdir_and_quarantine(self):
        original = self.source / "original.txt"
        original.write_text("original", encoding="utf-8")
        replace = self.source / "replace.txt"
        replace.write_text("before", encoding="utf-8")
        rename = self.destination / "rename.txt"
        rename.write_text("rename", encoding="utf-8")
        quarantine = self.source / "remove-me.txt"
        quarantine.write_text("recoverable", encoding="utf-8")

        actions = [
            self.create_action("created.txt", "created"),
            {
                "kind": "replace_text",
                "root_id": "source",
                "relative_path": "replace.txt",
                "content": "after",
            },
            {
                "kind": "copy",
                "source_root_id": "source",
                "source_relative_path": "original.txt",
                "destination_root_id": "destination",
                "destination_relative_path": "copied.txt",
            },
            {
                "kind": "move",
                "source_root_id": "source",
                "source_relative_path": "original.txt",
                "destination_root_id": "destination",
                "destination_relative_path": "moved.txt",
            },
            {
                "kind": "rename",
                "root_id": "destination",
                "source_relative_path": "rename.txt",
                "destination_relative_path": "renamed.txt",
            },
            {"kind": "mkdir", "root_id": "destination", "relative_path": "New Folder"},
            {
                "kind": "quarantine",
                "root_id": "source",
                "relative_path": "remove-me.txt",
            },
        ]
        result = self.operator.propose(actions)
        self.approve(result)
        applied = self.operator.apply(str(result["plan_id"]))
        self.assertEqual((self.source / "replace.txt").read_text(encoding='utf-8'), "after")
        self.assertEqual((self.destination / "copied.txt").read_text(encoding='utf-8'), "original")
        self.assertEqual((self.destination / "moved.txt").read_text(encoding='utf-8'), "original")
        self.assertFalse(original.exists())
        self.assertTrue((self.destination / "renamed.txt").exists())
        self.assertTrue((self.destination / "New Folder").is_dir())
        self.assertFalse(quarantine.exists())
        status = self.operator.operation_status(str(applied["operation_id"]))
        self.assertEqual(status["status"], "executed")
        self.assertTrue(all(step["verified"] for step in status["steps"]))

        self.operator.undo_operation(str(applied["operation_id"]))
        self.assertEqual(replace.read_text(encoding='utf-8'), "before")
        self.assertTrue(original.exists())
        self.assertTrue(rename.exists())
        self.assertTrue(quarantine.exists())
        self.assertFalse((self.destination / "created.txt").exists())
        self.assertFalse((self.destination / "copied.txt").exists())
        self.assertFalse((self.destination / "moved.txt").exists())
        self.assertFalse((self.destination / "renamed.txt").exists())
        self.assertFalse((self.destination / "New Folder").exists())

    def test_changed_source_and_destination_collision_are_rejected(self):
        source = self.source / "source.bin"
        source.write_bytes(b"before")
        result = self.operator.propose(
            [
                {
                    "kind": "copy",
                    "source_root_id": "source",
                    "source_relative_path": "source.bin",
                    "destination_root_id": "destination",
                    "destination_relative_path": "target.bin",
                }
            ]
        )
        self.approve(result)
        source.write_bytes(b"changed")
        with self.assertRaises(BrokerPolicyViolation):
            self.operator.apply(str(result["plan_id"]))
        self.assertFalse((self.destination / "target.bin").exists())

        fresh = self.operator.propose(
            [
                {
                    "kind": "copy",
                    "source_root_id": "source",
                    "source_relative_path": "source.bin",
                    "destination_root_id": "destination",
                    "destination_relative_path": "late.bin",
                }
            ]
        )
        self.approve(fresh)
        (self.destination / "late.bin").write_bytes(b"user data")
        with self.assertRaises(BrokerPolicyViolation):
            self.operator.apply(str(fresh["plan_id"]))
        self.assertEqual((self.destination / "late.bin").read_bytes(), b"user data")

    def test_batch_failure_rolls_back_prior_verified_steps(self):
        source = self.source / "source.txt"
        source.write_text("original", encoding="utf-8")
        result = self.operator.propose(
            [
                self.create_action("first.txt", "first"),
                {
                    "kind": "copy",
                    "source_root_id": "source",
                    "source_relative_path": "source.txt",
                    "destination_root_id": "destination",
                    "destination_relative_path": "second.txt",
                },
            ]
        )
        self.approve(result)
        source.write_text("changed after proposal", encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.operator.apply(str(result["plan_id"]))
        self.assertFalse((self.destination / "first.txt").exists())
        self.assertFalse((self.destination / "second.txt").exists())
        self.assertEqual(
            self.state.get_plan(str(result["plan_id"])).status, "failed_rolled_back"
        )

    def test_restart_reconciliation_rolls_back_prepared_or_performed_action(self):
        result = self.operator.propose([self.create_action("interrupted.txt", "temporary")])
        self.approve(result)
        plan, operation_id = self.state.claim(str(result["plan_id"]))
        action = plan.actions[0]
        undo = self.operator._prepare_undo(action, operation_id, 0)
        self.state.prepare_step(operation_id, 0, undo)
        self.operator._execute(action, undo)
        self.assertTrue((self.destination / "interrupted.txt").exists())

        restarted_state = OperatorStateStore(self.state.path, self.protector)
        restarted = PermissionedOperator(
            self.permissions, restarted_state, self.base / "Cypher Quarantine"
        )
        reconciliation = restarted.reconcile_incomplete()
        self.assertTrue(reconciliation["safe_to_start"])
        self.assertIn(operation_id, reconciliation["recovered_operations"])
        self.assertFalse((self.destination / "interrupted.txt").exists())

    def test_restart_reconciliation_removes_partial_staging_file(self):
        source = self.source / "large.bin"
        source.write_bytes(b"complete source")
        result = self.operator.propose(
            [
                {
                    "kind": "copy",
                    "source_root_id": "source",
                    "source_relative_path": "large.bin",
                    "destination_root_id": "destination",
                    "destination_relative_path": "copied.bin",
                }
            ]
        )
        self.approve(result)
        plan, operation_id = self.state.claim(str(result["plan_id"]))
        undo = self.operator._prepare_undo(plan.actions[0], operation_id, 0)
        self.state.prepare_step(operation_id, 0, undo)
        staging = Path(str(undo["staging_path"]))
        staging.write_bytes(b"partial")

        reconciliation = self.operator.reconcile_incomplete()
        self.assertTrue(reconciliation["safe_to_start"])
        self.assertFalse(staging.exists())
        self.assertFalse((self.destination / "copied.bin").exists())

    def test_restart_reconciliation_finishes_interrupted_human_undo(self):
        result = self.operator.propose([self.create_action("undo-restart.txt", "temporary")])
        self.approve(result)
        applied = self.operator.apply(str(result["plan_id"]))
        operation_id = str(applied["operation_id"])
        operation = self.state.operation(operation_id)
        self.state.begin_undo(operation_id, operation["plan_id"])

        reconciliation = self.operator.reconcile_incomplete()
        self.assertTrue(reconciliation["safe_to_start"])
        self.assertFalse((self.destination / "undo-restart.txt").exists())
        self.assertEqual(
            self.operator.operation_status(operation_id)["status"],
            "undone_after_restart",
        )

    def test_expired_approval_path_traversal_and_wrong_fingerprint_fail_closed(self):
        result = self.operator.propose([self.create_action("late.txt")])
        with self.assertRaises(BrokerPolicyViolation):
            self.state.approve(str(result["plan_id"]), "wrong")
        plan = self.state.get_plan(str(result["plan_id"]))
        with closing(sqlite3.connect(self.state.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE operator_plans SET expires_at=? WHERE plan_id=?",
                    ((utc_now() - timedelta(minutes=1)).isoformat(), plan.plan_id),
                )
        with self.assertRaises(BrokerPolicyViolation):
            self.state.approve(plan.plan_id, plan.fingerprint)
        for unsafe in ("../escape.txt", "C:\\Windows\\escape.txt", "CON.txt"):
            with self.subTest(path=unsafe), self.assertRaises(BrokerPolicyViolation):
                self.operator.propose([self.create_action(unsafe)])

    def test_audit_contains_metadata_not_paths_or_content(self):
        result = self.operator.propose(
            [self.create_action("private-client-name.txt", "private campaign content")]
        )
        self.approve(result)
        self.operator.apply(str(result["plan_id"]))
        audit = (self.base / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn(str(result["plan_id"]), audit)
        self.assertNotIn("private-client-name", audit)
        self.assertNotIn("private campaign content", audit)

    def test_mcp_exposes_proposal_apply_and_status_but_no_permission_mutation_or_undo(self):
        sandbox = self.base / "Hermes Sandbox"
        sandbox.mkdir()
        from local_assistant.capability_broker import ReadOnlyCapabilityBroker

        app = McpApplication(
            ReadOnlyCapabilityBroker(sandbox, self.base / "audit.jsonl"),
            operator=self.operator,
        )
        listed = app.dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = {item["name"] for item in listed["result"]["tools"]}
        self.assertIn("operator_permission_status", names)
        self.assertIn("operator_propose_plan", names)
        self.assertIn("operator_apply_approved_plan", names)
        self.assertNotIn("operator_add_permission", names)
        self.assertNotIn("operator_approve_plan", names)
        self.assertNotIn("operator_undo", names)

        proposed = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "operator_propose_plan",
                    "arguments": {"actions": [self.create_action("mcp.txt", "mcp")]},
                },
            }
        )
        self.assertFalse(proposed["result"]["isError"])
        plan_id = proposed["result"]["structuredContent"]["plan_id"]
        rejected = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "operator_apply_approved_plan",
                    "arguments": {"plan_id": plan_id},
                },
            }
        )
        self.assertTrue(rejected["result"]["isError"])
        plan = self.state.get_plan(plan_id)
        self.state.approve(plan.plan_id, plan.fingerprint)
        applied = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "operator_apply_approved_plan",
                    "arguments": {"plan_id": plan_id},
                },
            }
        )
        self.assertFalse(applied["result"]["isError"])
        self.assertEqual((self.destination / "mcp.txt").read_text(encoding='utf-8'), "mcp")

        private_path = "../private-client-name.txt"
        unsafe = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 5,
                "method": "tools/call",
                "params": {
                    "name": "operator_propose_plan",
                    "arguments": {"actions": [self.create_action(private_path, "secret")]},
                },
            }
        )
        self.assertTrue(unsafe["result"]["isError"])
        audit = (self.base / "audit.jsonl").read_text(encoding="utf-8")
        self.assertNotIn(private_path, audit)


class ProtectedPayloadTests(unittest.TestCase):
    def test_test_envelope_authenticates_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / "key"
            first = TestKeyProtector(key)
            protected = first.protect(b"sensitive")
            self.assertNotIn("sensitive", protected)
            second = TestKeyProtector(key)
            self.assertEqual(second.unprotect(protected), b"sensitive")
            damaged = protected[:-2] + "AA"
            with self.assertRaises(PayloadProtectionError):
                second.unprotect(damaged)


if __name__ == "__main__":
    unittest.main()
