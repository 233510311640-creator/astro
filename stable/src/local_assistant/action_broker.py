from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid
from typing import Iterator

from .capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker


PLAN_VERSION = 2
PROPOSAL_TTL_MINUTES = 60
APPROVED_EXECUTION_TTL_MINUTES = 10


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class ActionPlan:
    plan_id: str
    root: str
    kind: str
    payload: dict[str, object]
    fingerprint: str
    status: str
    created_at: str
    expires_at: str
    approved_expires_at: str | None = None
    operation_id: str | None = None


class ActionStateStore:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @contextmanager
    def _managed_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _init(self) -> None:
        with self._managed_connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS action_plans (
                    plan_id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_expires_at TEXT,
                    operation_id TEXT
                );
                CREATE TABLE IF NOT EXISTS action_operations (
                    operation_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL UNIQUE,
                    root TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    undo_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    undone_at TEXT,
                    FOREIGN KEY(plan_id) REFERENCES action_plans(plan_id)
                );
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(action_plans)").fetchall()
            }
            if "approved_expires_at" not in columns:
                connection.execute(
                    "ALTER TABLE action_plans ADD COLUMN approved_expires_at TEXT"
                )
            legacy_rows = connection.execute(
                """
                SELECT plan_id, approved_at FROM action_plans
                WHERE status='approved'
                  AND approved_at IS NOT NULL
                  AND approved_expires_at IS NULL
                """
            ).fetchall()
            for row in legacy_rows:
                approved_expires = datetime.fromisoformat(row["approved_at"]) + timedelta(
                    minutes=APPROVED_EXECUTION_TTL_MINUTES
                )
                connection.execute(
                    "UPDATE action_plans SET approved_expires_at=? WHERE plan_id=?",
                    (approved_expires.isoformat(), row["plan_id"]),
                )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ActionPlan:
        return ActionPlan(
            plan_id=row["plan_id"],
            root=row["root"],
            kind=row["kind"],
            payload=json.loads(row["payload_json"]),
            fingerprint=row["fingerprint"],
            status=row["status"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            approved_expires_at=row["approved_expires_at"],
            operation_id=row["operation_id"],
        )

    def create_plan(self, root: Path, kind: str, payload: dict[str, object]) -> ActionPlan:
        plan_id = str(uuid.uuid4())
        created = utc_now()
        expires = created + timedelta(minutes=PROPOSAL_TTL_MINUTES)
        fingerprint_payload = {
            "version": PLAN_VERSION,
            "plan_id": plan_id,
            "root": str(root),
            "kind": kind,
            "payload": payload,
            "expires_at": expires.isoformat(),
        }
        fingerprint = hashlib.sha256(canonical_json(fingerprint_payload).encode("utf-8")).hexdigest()
        with self._managed_connection() as connection:
            connection.execute(
                """
                INSERT INTO action_plans
                (plan_id, root, kind, payload_json, fingerprint, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, 'proposed', ?, ?)
                """,
                (
                    plan_id,
                    str(root),
                    kind,
                    canonical_json(payload),
                    fingerprint,
                    created.isoformat(),
                    expires.isoformat(),
                ),
            )
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: str) -> ActionPlan:
        with self._managed_connection() as connection:
            row = connection.execute(
                "SELECT * FROM action_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
        if row is None:
            raise BrokerPolicyViolation(f"Unknown plan: {plan_id}")
        return self._from_row(row)

    def list_plans(self, root: Path, limit: int = 20) -> list[ActionPlan]:
        with self._managed_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM action_plans WHERE root=? ORDER BY created_at DESC LIMIT ?",
                (str(root), limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def approve(self, plan_id: str, root: Path, fingerprint: str) -> ActionPlan:
        now = utc_now()
        rejection: str | None = None
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM action_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown plan: {plan_id}")
            plan = self._from_row(row)
            if row["root"] != str(root):
                raise BrokerPolicyViolation("Plan belongs to a different sandbox root")
            if plan.status != "proposed":
                raise BrokerPolicyViolation(f"Plan is not awaiting approval: {plan.status}")
            if datetime.fromisoformat(plan.expires_at) <= now:
                connection.execute(
                    "UPDATE action_plans SET status='expired' WHERE plan_id=?", (plan_id,)
                )
                rejection = "Plan has expired; create a new proposal"
            elif fingerprint != plan.fingerprint:
                raise BrokerPolicyViolation("Fingerprint mismatch")
            else:
                approved_expires = now + timedelta(minutes=APPROVED_EXECUTION_TTL_MINUTES)
                connection.execute(
                    """
                    UPDATE action_plans
                    SET status='approved', approved_at=?, approved_expires_at=?
                    WHERE plan_id=?
                    """,
                    (now.isoformat(), approved_expires.isoformat(), plan_id),
                )
        if rejection is not None:
            raise BrokerPolicyViolation(rejection)
        return self.get_plan(plan_id)

    def claim_approved(self, plan_id: str, root: Path) -> ActionPlan:
        now = utc_now()
        rejection: str | None = None
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM action_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown plan: {plan_id}")
            plan = self._from_row(row)
            if row["root"] != str(root):
                raise BrokerPolicyViolation("Plan belongs to a different sandbox root")
            if plan.status != "approved":
                raise BrokerPolicyViolation(f"Plan is not approved: {plan.status}")
            if plan.approved_expires_at is None:
                connection.execute(
                    "UPDATE action_plans SET status='expired' WHERE plan_id=?", (plan_id,)
                )
                rejection = "Approved plan has no execution window; create a new proposal"
            elif datetime.fromisoformat(plan.approved_expires_at) <= now:
                connection.execute(
                    "UPDATE action_plans SET status='expired' WHERE plan_id=?", (plan_id,)
                )
                rejection = "Post-approval execution window expired; create a new proposal"
            else:
                changed = connection.execute(
                    """
                    UPDATE action_plans SET status='applying'
                    WHERE plan_id=? AND status='approved'
                    """,
                    (plan_id,),
                ).rowcount
                if changed != 1:
                    raise BrokerPolicyViolation("Plan could not be claimed")
        if rejection is not None:
            raise BrokerPolicyViolation(rejection)
        return self.get_plan(plan_id)

    def finish_operation(
        self,
        plan: ActionPlan,
        root: Path,
        undo: dict[str, object],
        operation_id: str,
    ) -> None:
        now = utc_now().isoformat()
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO action_operations
                (operation_id, plan_id, root, kind, undo_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'executed', ?)
                """,
                (
                    operation_id,
                    plan.plan_id,
                    str(root),
                    plan.kind,
                    canonical_json(undo),
                    now,
                ),
            )
            connection.execute(
                "UPDATE action_plans SET status='executed', operation_id=? WHERE plan_id=?",
                (operation_id, plan.plan_id),
            )

    def mark_failed(self, plan_id: str) -> None:
        with self._managed_connection() as connection:
            connection.execute(
                "UPDATE action_plans SET status='failed' WHERE plan_id=? AND status='applying'",
                (plan_id,),
            )

    def get_operation(self, operation_id: str, root: Path) -> sqlite3.Row:
        with self._managed_connection() as connection:
            row = connection.execute(
                "SELECT * FROM action_operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
        if row is None:
            raise BrokerPolicyViolation(f"Unknown operation: {operation_id}")
        if row["root"] != str(root):
            raise BrokerPolicyViolation("Operation belongs to a different sandbox root")
        return row

    def mark_undone(self, operation_id: str) -> None:
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE action_operations SET status='undone', undone_at=?
                WHERE operation_id=? AND status='executed'
                """,
                (utc_now().isoformat(), operation_id),
            ).rowcount
            if changed != 1:
                raise BrokerPolicyViolation("Operation is not eligible for undo")


class ApprovedActionEngine:
    def __init__(self, broker: ReadOnlyCapabilityBroker, state: ActionStateStore):
        self.broker = broker
        self.state = state

    @staticmethod
    def _validate_content(content: str, limit: int) -> bytes:
        if not isinstance(content, str):
            raise BrokerPolicyViolation("content must be text")
        if "\x00" in content:
            raise BrokerPolicyViolation("NUL characters are not allowed")
        encoded = content.encode("utf-8")
        if len(encoded) > limit:
            raise BrokerPolicyViolation(f"Content exceeds {limit} UTF-8 bytes")
        return encoded

    def _validate_text_extension(self, path: Path) -> None:
        if path.suffix.casefold() not in self.broker.SAFE_TEXT_EXTENSIONS:
            raise BrokerPolicyViolation("Only approved plain-text file types may be changed")

    @staticmethod
    def _approval_summary(plan: ActionPlan, content_bytes: int | None) -> str:
        if plan.kind == "create_text":
            return (
                f"Create one UTF-8 text file at '{plan.payload.get('path')}' "
                f"({content_bytes or 0} bytes). Existing files will not be overwritten."
            )
        if plan.kind == "replace_text":
            return (
                f"Replace one UTF-8 text file at '{plan.payload.get('path')}' "
                f"({content_bytes or 0} bytes). Its current hash must still match; undo is available."
            )
        if plan.kind == "make_directory":
            return (
                f"Create one directory at '{plan.payload.get('path')}'. "
                "Existing items will not be overwritten."
            )
        if plan.kind == "move":
            return (
                f"Move or rename one item from '{plan.payload.get('source')}' to "
                f"'{plan.payload.get('destination')}'. No overwrite; undo is available."
            )
        return f"Apply one bounded '{plan.kind}' action inside the approved sandbox."

    @classmethod
    def public_plan(cls, plan: ActionPlan) -> dict[str, object]:
        payload = dict(plan.payload)
        content = payload.pop("content", None)
        content_bytes: int | None = None
        if isinstance(content, str):
            content_bytes = len(content.encode("utf-8"))
            payload["content_bytes"] = content_bytes
            payload["content_preview"] = content[:160]
        undo_available = plan.kind in {"replace_text", "move"}
        return {
            "plan_id": plan.plan_id,
            "kind": plan.kind,
            "details": payload,
            "fingerprint": plan.fingerprint,
            "approval_code": plan.fingerprint[-8:],
            "status": plan.status,
            "proposal_expires_at": plan.expires_at,
            "execution_expires_at": plan.approved_expires_at,
            "human_summary": cls._approval_summary(plan, content_bytes),
            "safety": {
                "scope": "Hermes Sandbox only",
                "overwrite_allowed": False,
                "approval": "one exact fingerprint",
                "undo_available": undo_available,
            },
            "approval_command": (
                ".\\scripts\\manage_capability_broker_windows.ps1 approve "
                f"{plan.plan_id}"
            ),
        }

    def propose_create_text(self, relative_path: str, content: str) -> dict[str, object]:
        target = self.broker.resolve_new_target(relative_path)
        self._validate_text_extension(target)
        self._validate_content(content, self.broker.limits.max_read_bytes)
        plan = self.state.create_plan(
            self.broker.root,
            "create_text",
            {"path": relative_path, "content": content},
        )
        return self.public_plan(plan)

    def propose_replace_text(self, relative_path: str, content: str) -> dict[str, object]:
        target = self.broker.resolve(relative_path, require_file=True)
        self._validate_text_extension(target)
        self._validate_content(content, self.broker.limits.max_read_bytes)
        current = target.read_bytes()
        if len(current) > self.broker.limits.max_read_bytes or b"\x00" in current:
            raise BrokerPolicyViolation("Existing file is not an approved small text file")
        plan = self.state.create_plan(
            self.broker.root,
            "replace_text",
            {
                "path": relative_path,
                "content": content,
                "expected_sha256": sha256_bytes(current),
            },
        )
        return self.public_plan(plan)

    def propose_make_directory(self, relative_path: str) -> dict[str, object]:
        self.broker.resolve_new_target(relative_path)
        plan = self.state.create_plan(
            self.broker.root, "make_directory", {"path": relative_path}
        )
        return self.public_plan(plan)

    def propose_move(self, source: str, destination: str) -> dict[str, object]:
        source_path = self.broker.resolve(source)
        if source_path == self.broker.root:
            raise BrokerPolicyViolation("Sandbox root cannot be moved")
        destination_path = self.broker.resolve_new_target(destination)
        if source_path.is_dir():
            try:
                destination_path.relative_to(source_path)
            except ValueError:
                pass
            else:
                raise BrokerPolicyViolation("A directory cannot be moved inside itself")
        plan = self.state.create_plan(
            self.broker.root,
            "move",
            {"source": source, "destination": destination},
        )
        return self.public_plan(plan)

    def apply(self, plan_id: str) -> dict[str, object]:
        plan = self.state.claim_approved(plan_id, self.broker.root)
        operation_id = str(uuid.uuid4())
        undo: dict[str, object] | None = None
        try:
            undo = self._execute(plan)
            self.state.finish_operation(plan, self.broker.root, undo, operation_id)
        except Exception:
            if undo is not None:
                self._perform_undo_payload(undo)
            self.state.mark_failed(plan.plan_id)
            raise
        self.broker.audit.record(
            "sandbox_apply_approved_plan", "[approved-plan]", True,
            plan_id=plan.plan_id, operation_id=operation_id, kind=plan.kind
        )
        return {
            "status": "executed",
            "plan_id": plan.plan_id,
            "operation_id": operation_id,
            "kind": plan.kind,
            "undo_command": (
                ".\\scripts\\manage_capability_broker_windows.ps1 undo "
                f"{operation_id}"
            ),
        }

    def _execute(self, plan: ActionPlan) -> dict[str, object]:
        payload = plan.payload
        if plan.kind == "create_text":
            path = self.broker.resolve_new_target(str(payload["path"]))
            data = self._validate_content(str(payload["content"]), self.broker.limits.max_read_bytes)
            self._validate_text_extension(path)
            try:
                with path.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            except Exception:
                if path.exists() and path.is_file():
                    path.unlink()
                raise
            return {"kind": "remove_created_file", "path": str(payload["path"]), "sha256": sha256_bytes(data)}
        if plan.kind == "replace_text":
            path = self.broker.resolve(str(payload["path"]), require_file=True)
            old = path.read_bytes()
            if sha256_bytes(old) != payload["expected_sha256"]:
                raise BrokerPolicyViolation("Target changed after proposal; create a new plan")
            new = self._validate_content(str(payload["content"]), self.broker.limits.max_read_bytes)
            temporary = path.with_name(f".{path.name}.broker-{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(new)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
            return {
                "kind": "restore_text",
                "path": str(payload["path"]),
                "expected_sha256": sha256_bytes(new),
                "old_base64": base64.b64encode(old).decode("ascii"),
            }
        if plan.kind == "make_directory":
            path = self.broker.resolve_new_target(str(payload["path"]))
            path.mkdir()
            return {"kind": "remove_empty_directory", "path": str(payload["path"])}
        if plan.kind == "move":
            source = self.broker.resolve(str(payload["source"]))
            destination = self.broker.resolve_new_target(str(payload["destination"]))
            source.rename(destination)
            return {
                "kind": "move_back",
                "source": str(payload["source"]),
                "destination": str(payload["destination"]),
            }
        raise BrokerPolicyViolation(f"Unsupported plan kind: {plan.kind}")

    def undo(self, operation_id: str) -> dict[str, object]:
        row = self.state.get_operation(operation_id, self.broker.root)
        if row["status"] != "executed":
            raise BrokerPolicyViolation(f"Operation cannot be undone: {row['status']}")
        undo = json.loads(row["undo_json"])
        kind = undo["kind"]
        self._perform_undo_payload(undo)
        self.state.mark_undone(operation_id)
        self.broker.audit.record(
            "operator_undo", "[operation]", True, operation_id=operation_id, kind=kind
        )
        return {"status": "undone", "operation_id": operation_id, "kind": kind}

    def _perform_undo_payload(self, undo: dict[str, object]) -> None:
        kind = undo["kind"]
        if kind == "remove_created_file":
            path = self.broker.resolve(str(undo["path"]), require_file=True)
            if sha256_bytes(path.read_bytes()) != undo["sha256"]:
                raise BrokerPolicyViolation("Created file changed; refusing destructive undo")
            path.unlink()
        elif kind == "restore_text":
            path = self.broker.resolve(str(undo["path"]), require_file=True)
            if sha256_bytes(path.read_bytes()) != undo["expected_sha256"]:
                raise BrokerPolicyViolation("Edited file changed; refusing to overwrite during undo")
            old = base64.b64decode(undo["old_base64"], validate=True)
            temporary = path.with_name(f".{path.name}.undo-{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(old)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
        elif kind == "remove_empty_directory":
            path = self.broker.resolve(str(undo["path"]), require_dir=True)
            path.rmdir()
        elif kind == "move_back":
            source_text = str(undo["source"])
            destination = self.broker.resolve(str(undo["destination"]))
            source = self.broker.resolve_new_target(source_text)
            destination.rename(source)
        else:
            raise BrokerPolicyViolation(f"Unsupported undo kind: {kind}")
