from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest

from local_assistant.action_broker import (
    APPROVED_EXECUTION_TTL_MINUTES,
    PROPOSAL_TTL_MINUTES,
    ActionStateStore,
    ApprovedActionEngine,
    utc_now,
)
from local_assistant.broker_mcp import McpApplication
from local_assistant.capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker


class ApprovedActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "Hermes Sandbox"
        self.root.mkdir()
        self.broker = ReadOnlyCapabilityBroker(self.root, self.base / "audit.jsonl")
        self.state = ActionStateStore(self.base / "action_state.db")
        self.engine = ApprovedActionEngine(self.broker, self.state)

    def tearDown(self):
        self.temp.cleanup()

    def approve(self, plan_result: dict[str, object]):
        plan = self.state.get_plan(str(plan_result["plan_id"]))
        return self.state.approve(plan.plan_id, self.root.resolve(), plan.fingerprint)

    def test_proposal_makes_no_change_and_unapproved_apply_fails(self):
        plan = self.engine.propose_create_text("draft.txt", "hello")
        self.assertFalse((self.root / "draft.txt").exists())

    def test_proposal_has_deterministic_human_summary_and_safety_facts(self):
        plan = self.engine.propose_create_text("draft.txt", "hello")
        self.assertEqual(
            plan["human_summary"],
            "Create one UTF-8 text file at 'draft.txt' (5 bytes). "
            "Existing files will not be overwritten.",
        )
        self.assertEqual(plan["safety"]["scope"], "Hermes Sandbox only")
        self.assertFalse(plan["safety"]["overwrite_allowed"])
        self.assertFalse(plan["safety"]["undo_available"])
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.apply(str(plan["plan_id"]))
        self.assertFalse((self.root / "draft.txt").exists())

    def test_wrong_fingerprint_cannot_approve(self):
        result = self.engine.propose_create_text("draft.txt", "hello")
        with self.assertRaises(BrokerPolicyViolation):
            self.state.approve(str(result["plan_id"]), self.root.resolve(), "wrong")
        self.assertEqual(self.state.get_plan(str(result["plan_id"])).status, "proposed")

    def test_approved_create_executes_once_and_undoes(self):
        result = self.engine.propose_create_text("draft.txt", "hello")
        self.approve(result)
        applied = self.engine.apply(str(result["plan_id"]))
        self.assertEqual((self.root / "draft.txt").read_text(encoding="utf-8"), "hello")
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.apply(str(result["plan_id"]))
        undone = self.engine.undo(str(applied["operation_id"]))
        self.assertEqual(undone["status"], "undone")
        self.assertFalse((self.root / "draft.txt").exists())
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.undo(str(applied["operation_id"]))

    def test_create_refuses_late_overwrite(self):
        result = self.engine.propose_create_text("draft.txt", "planned")
        self.approve(result)
        (self.root / "draft.txt").write_text("someone else", encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.apply(str(result["plan_id"]))
        self.assertEqual((self.root / "draft.txt").read_text(encoding="utf-8"), "someone else")

    def test_replace_requires_unchanged_target_and_undo_preserves_changes(self):
        target = self.root / "note.txt"
        target.write_text("before", encoding="utf-8")
        stale = self.engine.propose_replace_text("note.txt", "after")
        self.approve(stale)
        target.write_text("changed elsewhere", encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.apply(str(stale["plan_id"]))
        self.assertEqual(target.read_text(encoding="utf-8"), "changed elsewhere")

        fresh = self.engine.propose_replace_text("note.txt", "approved replacement")
        self.approve(fresh)
        applied = self.engine.apply(str(fresh["plan_id"]))
        self.assertEqual(target.read_text(encoding="utf-8"), "approved replacement")
        target.write_text("newer user change", encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.engine.undo(str(applied["operation_id"]))
        self.assertEqual(target.read_text(encoding="utf-8"), "newer user change")

    def test_directory_and_move_are_reversible_without_overwrite(self):
        directory_plan = self.engine.propose_make_directory("Project")
        self.approve(directory_plan)
        directory_operation = self.engine.apply(str(directory_plan["plan_id"]))
        self.assertTrue((self.root / "Project").is_dir())
        self.engine.undo(str(directory_operation["operation_id"]))
        self.assertFalse((self.root / "Project").exists())

        source = self.root / "one.txt"
        source.write_text("one", encoding="utf-8")
        move_plan = self.engine.propose_move("one.txt", "two.txt")
        self.approve(move_plan)
        move_operation = self.engine.apply(str(move_plan["plan_id"]))
        self.assertFalse(source.exists())
        self.assertTrue((self.root / "two.txt").exists())
        self.engine.undo(str(move_operation["operation_id"]))
        self.assertTrue(source.exists())
        self.assertFalse((self.root / "two.txt").exists())

    def test_nonempty_created_directory_is_not_removed_by_undo(self):
        result = self.engine.propose_make_directory("Project")
        self.approve(result)
        applied = self.engine.apply(str(result["plan_id"]))
        (self.root / "Project" / "user.txt").write_text("keep", encoding="utf-8")
        with self.assertRaises(OSError):
            self.engine.undo(str(applied["operation_id"]))
        self.assertTrue((self.root / "Project" / "user.txt").exists())

    def test_expired_plan_cannot_be_approved(self):
        result = self.engine.propose_create_text("late.txt", "late")
        expired = (utc_now() - timedelta(minutes=1)).isoformat()
        with closing(sqlite3.connect(self.state.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE action_plans SET expires_at=? WHERE plan_id=?",
                    (expired, str(result["plan_id"])),
                )
        plan = self.state.get_plan(str(result["plan_id"]))
        with self.assertRaises(BrokerPolicyViolation):
            self.state.approve(plan.plan_id, self.root.resolve(), plan.fingerprint)
        self.assertEqual(self.state.get_plan(plan.plan_id).status, "expired")
        self.assertFalse((self.root / "late.txt").exists())

    def test_approval_opens_a_fresh_execution_window(self):
        result = self.engine.propose_create_text("fresh-window.txt", "approved")
        approved = self.approve(result)
        proposal_created = datetime.fromisoformat(approved.created_at)
        proposal_expires = datetime.fromisoformat(approved.expires_at)
        execution_expires = datetime.fromisoformat(str(approved.approved_expires_at))
        self.assertAlmostEqual(
            (proposal_expires - proposal_created).total_seconds(),
            PROPOSAL_TTL_MINUTES * 60,
            delta=1,
        )
        self.assertAlmostEqual(
            (execution_expires - utc_now()).total_seconds(),
            APPROVED_EXECUTION_TTL_MINUTES * 60,
            delta=2,
        )

        proposal_expired = (utc_now() - timedelta(minutes=1)).isoformat()
        with closing(sqlite3.connect(self.state.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE action_plans SET expires_at=? WHERE plan_id=?",
                    (proposal_expired, str(result["plan_id"])),
                )
        applied = self.engine.apply(str(result["plan_id"]))
        self.assertEqual(applied["status"], "executed")
        self.assertEqual(
            (self.root / "fresh-window.txt").read_text(encoding="utf-8"), "approved"
        )

    def test_expired_post_approval_execution_window_is_rejected(self):
        result = self.engine.propose_create_text("too-late.txt", "late")
        self.approve(result)
        expired = (utc_now() - timedelta(minutes=1)).isoformat()
        with closing(sqlite3.connect(self.state.path)) as connection:
            with connection:
                connection.execute(
                    "UPDATE action_plans SET approved_expires_at=? WHERE plan_id=?",
                    (expired, str(result["plan_id"])),
                )
        with self.assertRaisesRegex(
            BrokerPolicyViolation, "Post-approval execution window expired"
        ):
            self.engine.apply(str(result["plan_id"]))
        self.assertEqual(self.state.get_plan(str(result["plan_id"])).status, "expired")
        self.assertFalse((self.root / "too-late.txt").exists())

    def test_v032_state_schema_is_migrated_without_losing_approved_plan(self):
        legacy_path = self.base / "legacy-v032.db"
        approved_at = utc_now().isoformat()
        with closing(sqlite3.connect(legacy_path)) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE action_plans (
                        plan_id TEXT PRIMARY KEY,
                        root TEXT NOT NULL,
                        kind TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        fingerprint TEXT NOT NULL,
                        status TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        expires_at TEXT NOT NULL,
                        approved_at TEXT,
                        operation_id TEXT
                    );
                    """
                )
                connection.execute(
                    """
                    INSERT INTO action_plans
                    (plan_id, root, kind, payload_json, fingerprint, status,
                     created_at, expires_at, approved_at, operation_id)
                    VALUES (?, ?, 'create_text', ?, 'legacy-fingerprint', 'approved',
                            ?, ?, ?, NULL)
                    """,
                    (
                        "legacy-plan",
                        str(self.root.resolve()),
                        '{"content":"legacy","path":"legacy.txt"}',
                        approved_at,
                        (utc_now() + timedelta(minutes=30)).isoformat(),
                        approved_at,
                    ),
                )

        migrated = ActionStateStore(legacy_path).get_plan("legacy-plan")
        self.assertIsNotNone(migrated.approved_expires_at)
        self.assertAlmostEqual(
            (
                datetime.fromisoformat(str(migrated.approved_expires_at))
                - datetime.fromisoformat(approved_at)
            ).total_seconds(),
            APPROVED_EXECUTION_TTL_MINUTES * 60,
            delta=1,
        )

    def test_plan_persists_across_independent_store_instances(self):
        result = self.engine.propose_create_text("persistent.txt", "saved")
        second_state = ActionStateStore(self.state.path)
        second_engine = ApprovedActionEngine(self.broker, second_state)
        plan = second_state.get_plan(str(result["plan_id"]))
        second_state.approve(plan.plan_id, self.root.resolve(), plan.fingerprint)
        second_engine.apply(plan.plan_id)
        self.assertEqual(
            (self.root / "persistent.txt").read_text(encoding="utf-8"), "saved"
        )

    def test_action_paths_cannot_escape_sandbox(self):
        cases = (
            lambda: self.engine.propose_create_text("../escape.txt", "x"),
            lambda: self.engine.propose_make_directory("C:\\Windows\\test"),
        )
        for case in cases:
            with self.subTest(case=case), self.assertRaises(BrokerPolicyViolation):
                case()

    def test_state_commit_failure_rolls_back_filesystem_change(self):
        target = self.root / "note.txt"
        target.write_text("before", encoding="utf-8")
        result = self.engine.propose_replace_text("note.txt", "after")
        self.approve(result)
        original_finish = self.state.finish_operation

        def fail_finish(*args, **kwargs):
            raise sqlite3.OperationalError("simulated state failure")

        self.state.finish_operation = fail_finish
        try:
            with self.assertRaises(sqlite3.OperationalError):
                self.engine.apply(str(result["plan_id"]))
        finally:
            self.state.finish_operation = original_finish
        self.assertEqual(target.read_text(encoding="utf-8"), "before")
        self.assertEqual(self.state.get_plan(str(result["plan_id"])).status, "failed")

    def test_state_store_explicitly_closes_every_connection(self):
        source = (Path(__file__).parents[1] / "src" / "local_assistant" / "action_broker.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("with self._connect() as connection", source)
        self.assertIn("connection.close()", source)

    def test_complete_mcp_propose_approve_apply_flow(self):
        app = McpApplication(self.broker, self.engine)
        proposed = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "sandbox_propose_create_text",
                    "arguments": {"relative_path": "mcp.txt", "content": "approved"},
                },
            }
        )
        self.assertFalse(proposed["result"]["isError"])
        plan_id = proposed["result"]["structuredContent"]["plan_id"]
        self.assertFalse((self.root / "mcp.txt").exists())
        plan = self.state.get_plan(plan_id)
        self.state.approve(plan.plan_id, self.root.resolve(), plan.fingerprint)
        applied = app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "sandbox_apply_approved_plan",
                    "arguments": {"plan_id": plan_id},
                },
            }
        )
        self.assertFalse(applied["result"]["isError"])
        self.assertEqual((self.root / "mcp.txt").read_text(encoding="utf-8"), "approved")

    def test_mcp_rejects_nonobject_params(self):
        app = McpApplication(self.broker, self.engine)
        response = app.dispatch(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": []}
        )
        self.assertEqual(response["error"]["code"], -32602)


if __name__ == "__main__":
    unittest.main()
