from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import wraps
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePath
import sqlite3
from typing import Callable, Iterator
import uuid

from .capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker
from .permission_center import PermissionCenter, PermissionRoot
from .protected_payload import PayloadProtectionError, PayloadProtector


OPERATOR_PLAN_VERSION = 1
PLAN_REVIEW_TTL_MINUTES = 60
APPROVED_EXECUTION_TTL_MINUTES = 10
MAX_OPERATOR_ITEMS = 50
MAX_TEXT_BYTES = 65_536
MAX_SINGLE_FILE_BYTES = 512 * 1024 * 1024
MAX_BATCH_BYTES = 2 * 1024 * 1024 * 1024
HASH_CHUNK_BYTES = 1024 * 1024


def exclusive_execution(method):
    """Serialize file execution across native and broker processes sharing this journal."""
    @wraps(method)
    def wrapped(self, *args, **kwargs):
        lock_path = self.state.path.with_suffix(self.state.path.suffix + '.execution.lock')
        with lock_path.open('a+b') as stream:
            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b'0'); stream.flush()
            stream.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise BrokerPolicyViolation('Another file operation is active; wait for its receipt') from exc
            try:
                return method(self, *args, **kwargs)
            finally:
                stream.seek(0)
                if os.name == 'nt': msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
    return wrapped


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_snapshot(path: Path, *, include_hash: bool = True) -> dict[str, object]:
    info = path.stat(follow_symlinks=False)
    result: dict[str, object] = {
        "size_bytes": info.st_size,
        "modified_ns": info.st_mtime_ns,
        "device_id": info.st_dev,
        "file_id": info.st_ino,
    }
    if include_hash:
        result["sha256"] = sha256_file(path)
    return result


@dataclass(frozen=True)
class OperatorPlan:
    plan_id: str
    actions: list[dict[str, object]]
    fingerprint: str
    status: str
    created_at: str
    expires_at: str
    approved_expires_at: str | None = None
    operation_id: str | None = None


class OperatorStateStore:
    """Encrypted plans plus metadata-only execution journal."""

    def __init__(self, path: Path, protector: PayloadProtector):
        self.path = path
        self.protector = protector
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
                CREATE TABLE IF NOT EXISTS operator_plans (
                    plan_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    payload_protected TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    approved_at TEXT,
                    approved_expires_at TEXT,
                    operation_id TEXT
                );
                CREATE TABLE IF NOT EXISTS operator_operations (
                    operation_id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL UNIQUE,
                    status TEXT NOT NULL,
                    item_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY(plan_id) REFERENCES operator_plans(plan_id)
                );
                CREATE TABLE IF NOT EXISTS operator_steps (
                    operation_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    kind TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    undo_protected TEXT,
                    status TEXT NOT NULL,
                    verification_json TEXT,
                    PRIMARY KEY(operation_id, step_index),
                    FOREIGN KEY(operation_id) REFERENCES operator_operations(operation_id)
                );
                """
            )

    @staticmethod
    def _fingerprint_actions(actions: list[dict[str, object]]) -> list[dict[str, object]]:
        sanitized: list[dict[str, object]] = []
        for action in actions:
            item = dict(action)
            content = item.pop("content", None)
            if isinstance(content, str):
                encoded = content.encode("utf-8")
                item["content_bytes"] = len(encoded)
                item["content_sha256"] = sha256_bytes(encoded)
            sanitized.append(item)
        return sanitized

    @classmethod
    def calculate_fingerprint(
        cls, plan_id: str, actions: list[dict[str, object]], expires_at: str
    ) -> str:
        payload = {
            "version": OPERATOR_PLAN_VERSION,
            "plan_id": plan_id,
            "actions": cls._fingerprint_actions(actions),
            "expires_at": expires_at,
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    def _protect_json(self, payload: object) -> str:
        return self.protector.protect(canonical_json(payload).encode("utf-8"))

    def _unprotect_json(self, protected: str) -> object:
        try:
            raw = self.protector.unprotect(protected)
            return json.loads(raw.decode("utf-8"))
        except (PayloadProtectionError, UnicodeError, json.JSONDecodeError) as exc:
            raise BrokerPolicyViolation("Protected operator state could not be authenticated") from exc

    def create_plan(self, actions: list[dict[str, object]]) -> OperatorPlan:
        plan_id = str(uuid.uuid4())
        created = utc_now()
        expires = created + timedelta(minutes=PLAN_REVIEW_TTL_MINUTES)
        fingerprint = self.calculate_fingerprint(plan_id, actions, expires.isoformat())
        protected = self._protect_json(actions)
        with self._managed_connection() as connection:
            connection.execute(
                """
                INSERT INTO operator_plans
                (plan_id, version, payload_protected, fingerprint, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, 'proposed', ?, ?)
                """,
                (
                    plan_id,
                    OPERATOR_PLAN_VERSION,
                    protected,
                    fingerprint,
                    created.isoformat(),
                    expires.isoformat(),
                ),
            )
        return self.get_plan(plan_id)

    def _from_plan_row(self, row: sqlite3.Row) -> OperatorPlan:
        if row["version"] != OPERATOR_PLAN_VERSION:
            raise BrokerPolicyViolation("Operator plan version is unsupported")
        actions = self._unprotect_json(row["payload_protected"])
        if not isinstance(actions, list) or not all(isinstance(item, dict) for item in actions):
            raise BrokerPolicyViolation("Protected operator plan has an invalid structure")
        expected = self.calculate_fingerprint(row["plan_id"], actions, row["expires_at"])
        if not isinstance(row["fingerprint"], str) or not hmac.compare_digest(
            row["fingerprint"], expected
        ):
            raise BrokerPolicyViolation("Operator plan fingerprint does not match protected state")
        return OperatorPlan(
            plan_id=row["plan_id"],
            actions=actions,
            fingerprint=row["fingerprint"],
            status=row["status"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            approved_expires_at=row["approved_expires_at"],
            operation_id=row["operation_id"],
        )

    def get_plan(self, plan_id: str) -> OperatorPlan:
        if not isinstance(plan_id, str) or not plan_id:
            raise BrokerPolicyViolation("plan_id must be non-empty text")
        with self._managed_connection() as connection:
            row = connection.execute(
                "SELECT * FROM operator_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
        if row is None:
            raise BrokerPolicyViolation(f"Unknown operator plan: {plan_id}")
        return self._from_plan_row(row)

    def list_plans(self, limit: int = 20) -> list[OperatorPlan]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
            raise BrokerPolicyViolation("Plan list limit must be from 1 to 100")
        with self._managed_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM operator_plans ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._from_plan_row(row) for row in rows]

    def approve(self, plan_id: str, fingerprint: str) -> OperatorPlan:
        now = utc_now()
        rejection: str | None = None
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM operator_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown operator plan: {plan_id}")
            plan = self._from_plan_row(row)
            if plan.status != "proposed":
                raise BrokerPolicyViolation(f"Plan is not awaiting approval: {plan.status}")
            if datetime.fromisoformat(plan.expires_at) <= now:
                connection.execute(
                    "UPDATE operator_plans SET status='expired' WHERE plan_id=?", (plan_id,)
                )
                rejection = "Operator plan expired; create a new proposal"
            elif not hmac.compare_digest(plan.fingerprint, fingerprint):
                raise BrokerPolicyViolation("Operator plan fingerprint mismatch")
            else:
                execution_expires = now + timedelta(
                    minutes=APPROVED_EXECUTION_TTL_MINUTES
                )
                connection.execute(
                    """
                    UPDATE operator_plans
                    SET status='approved', approved_at=?, approved_expires_at=?
                    WHERE plan_id=?
                    """,
                    (now.isoformat(), execution_expires.isoformat(), plan_id),
                )
        if rejection is not None:
            raise BrokerPolicyViolation(rejection)
        return self.get_plan(plan_id)

    def reject(self, plan_id: str, fingerprint: str) -> None:
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM operator_plans WHERE plan_id=?", (plan_id,)).fetchone()
            if row is None:
                raise BrokerPolicyViolation("Unknown operator plan")
            plan = self._from_plan_row(row)
            if plan.status != "proposed" or not hmac.compare_digest(plan.fingerprint, fingerprint):
                raise BrokerPolicyViolation("Proposal changed before rejection")
            connection.execute("UPDATE operator_plans SET status='denied' WHERE plan_id=?", (plan_id,))

    def claim(self, plan_id: str) -> tuple[OperatorPlan, str]:
        now = utc_now()
        rejection: str | None = None
        operation_id = str(uuid.uuid4())
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM operator_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown operator plan: {plan_id}")
            plan = self._from_plan_row(row)
            if plan.status != "approved":
                raise BrokerPolicyViolation(f"Plan is not approved: {plan.status}")
            if plan.approved_expires_at is None or datetime.fromisoformat(
                plan.approved_expires_at
            ) <= now:
                connection.execute(
                    "UPDATE operator_plans SET status='expired' WHERE plan_id=?", (plan_id,)
                )
                rejection = "Approved operator plan expired; create a new proposal"
            else:
                connection.execute(
                    """
                    INSERT INTO operator_operations
                    (operation_id, plan_id, status, item_count, created_at)
                    VALUES (?, ?, 'applying', ?, ?)
                    """,
                    (operation_id, plan_id, len(plan.actions), now.isoformat()),
                )
                for index, action in enumerate(plan.actions):
                    metadata = {
                        "kind": action.get("kind"),
                        "source_root_id": action.get("source_root_id") or action.get("root_id"),
                        "destination_root_id": action.get("destination_root_id"),
                        "size_bytes": action.get("size_bytes") or action.get("content_bytes"),
                    }
                    connection.execute(
                        """
                        INSERT INTO operator_steps
                        (operation_id, step_index, kind, metadata_json, status)
                        VALUES (?, ?, ?, ?, 'planned')
                        """,
                        (operation_id, index, str(action["kind"]), canonical_json(metadata)),
                    )
                connection.execute(
                    """
                    UPDATE operator_plans SET status='applying', operation_id=?
                    WHERE plan_id=?
                    """,
                    (operation_id, plan_id),
                )
        if rejection is not None:
            raise BrokerPolicyViolation(rejection)
        return self.get_plan(plan_id), operation_id

    def prepare_step(self, operation_id: str, index: int, undo: dict[str, object]) -> None:
        protected = self._protect_json(undo)
        with self._managed_connection() as connection:
            changed = connection.execute(
                """
                UPDATE operator_steps SET undo_protected=?, status='prepared'
                WHERE operation_id=? AND step_index=? AND status='planned'
                """,
                (protected, operation_id, index),
            ).rowcount
            if changed != 1:
                raise BrokerPolicyViolation("Operator step could not enter prepared state")

    def mark_step_performed(self, operation_id: str, index: int) -> None:
        with self._managed_connection() as connection:
            changed = connection.execute(
                """
                UPDATE operator_steps SET status='performed'
                WHERE operation_id=? AND step_index=? AND status='prepared'
                """,
                (operation_id, index),
            ).rowcount
            if changed != 1:
                raise BrokerPolicyViolation("Operator step could not enter performed state")

    def mark_step_verified(
        self, operation_id: str, index: int, verification: dict[str, object]
    ) -> None:
        with self._managed_connection() as connection:
            changed = connection.execute(
                """
                UPDATE operator_steps SET status='verified', verification_json=?
                WHERE operation_id=? AND step_index=? AND status='performed'
                """,
                (canonical_json(verification), operation_id, index),
            ).rowcount
            if changed != 1:
                raise BrokerPolicyViolation("Operator step could not enter verified state")

    def operation_steps(self, operation_id: str) -> list[sqlite3.Row]:
        with self._managed_connection() as connection:
            rows = connection.execute(
                """
                SELECT * FROM operator_steps
                WHERE operation_id=? ORDER BY step_index ASC
                """,
                (operation_id,),
            ).fetchall()
        return rows

    def step_undo(self, row: sqlite3.Row) -> dict[str, object]:
        if row["undo_protected"] is None:
            raise BrokerPolicyViolation("Operator step has no protected recovery record")
        value = self._unprotect_json(row["undo_protected"])
        if not isinstance(value, dict):
            raise BrokerPolicyViolation("Operator recovery record is invalid")
        return value

    def mark_step_rolled_back(self, operation_id: str, index: int) -> None:
        with self._managed_connection() as connection:
            connection.execute(
                """
                UPDATE operator_steps SET status='rolled_back'
                WHERE operation_id=? AND step_index=?
                """,
                (operation_id, index),
            )

    def finish(self, plan_id: str, operation_id: str) -> None:
        now = utc_now().isoformat()
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            remaining = connection.execute(
                """
                SELECT COUNT(*) FROM operator_steps
                WHERE operation_id=? AND status!='verified'
                """,
                (operation_id,),
            ).fetchone()[0]
            if remaining:
                raise BrokerPolicyViolation("Operator operation has unverified steps")
            connection.execute(
                "UPDATE operator_operations SET status='executed', completed_at=? WHERE operation_id=?",
                (now, operation_id),
            )
            connection.execute(
                "UPDATE operator_plans SET status='executed' WHERE plan_id=?",
                (plan_id,),
            )

    def set_operation_status(self, operation_id: str, plan_id: str, status: str) -> None:
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE operator_operations SET status=?, completed_at=? WHERE operation_id=?",
                (status, utc_now().isoformat(), operation_id),
            )
            connection.execute(
                "UPDATE operator_plans SET status=? WHERE plan_id=?", (status, plan_id)
            )

    def begin_undo(self, operation_id: str, plan_id: str) -> None:
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            changed = connection.execute(
                """
                UPDATE operator_operations SET status='undoing', completed_at=NULL
                WHERE operation_id=? AND plan_id=? AND status='executed'
                """,
                (operation_id, plan_id),
            ).rowcount
            if changed != 1:
                raise BrokerPolicyViolation("Operation could not enter undoing state")
            connection.execute(
                "UPDATE operator_plans SET status='undoing' WHERE plan_id=?",
                (plan_id,),
            )

    def operation(self, operation_id: str) -> sqlite3.Row:
        with self._managed_connection() as connection:
            row = connection.execute(
                "SELECT * FROM operator_operations WHERE operation_id=?", (operation_id,)
            ).fetchone()
        if row is None:
            raise BrokerPolicyViolation(f"Unknown operator operation: {operation_id}")
        return row

    def incomplete_operations(self) -> list[sqlite3.Row]:
        with self._managed_connection() as connection:
            return connection.execute(
                """
                SELECT * FROM operator_operations
                WHERE status IN ('applying', 'undoing', 'recovery_required')
                ORDER BY created_at
                """
            ).fetchall()


class OperatorCancelled(BrokerPolicyViolation):
    """Stop observed between atomic steps; rollback has been attempted."""


class PermissionedOperator:
    """Approval-gated, verified and reversible operations on scoped real folders."""

    def __init__(
        self,
        permissions: PermissionCenter,
        state: OperatorStateStore,
        quarantine_root: Path,
    ):
        self.permissions = permissions
        self.state = state
        self.quarantine_root = quarantine_root.expanduser().absolute()

    def _ensure_quarantine_root(self) -> Path:
        current = Path(self.quarantine_root.anchor)
        for part in self.quarantine_root.parts[1:]:
            current = current / part
            if current.exists() and ReadOnlyCapabilityBroker._is_reparse_point(current):
                raise BrokerPolicyViolation(
                    "The protected quarantine path cannot contain links or reparse points"
                )
        self.quarantine_root.mkdir(parents=True, exist_ok=True)
        if not self.quarantine_root.is_dir() or ReadOnlyCapabilityBroker._is_reparse_point(
            self.quarantine_root
        ):
            raise BrokerPolicyViolation("The protected quarantine path is invalid")
        return self.quarantine_root

    @staticmethod
    def _require_exact_keys(
        action: dict[str, object], required: set[str], optional: set[str] | None = None
    ) -> None:
        optional = optional or set()
        keys = set(action)
        if not required.issubset(keys) or keys - required - optional:
            expected = ", ".join(sorted(required))
            raise BrokerPolicyViolation(
                f"Action must contain exactly the required fields for its kind: {expected}"
            )

    @staticmethod
    def _text(value: object, name: str) -> str:
        if not isinstance(value, str):
            raise BrokerPolicyViolation(f"{name} must be text")
        return value

    @staticmethod
    def _canonical_relative(record: PermissionRoot, path: Path) -> str:
        try:
            return path.relative_to(record.path).as_posix()
        except ValueError as exc:
            raise BrokerPolicyViolation("Resolved path escaped its permission root") from exc

    @staticmethod
    def _validate_text(path: Path, content: object) -> tuple[str, bytes]:
        if path.suffix.casefold() not in ReadOnlyCapabilityBroker.SAFE_TEXT_EXTENSIONS:
            raise BrokerPolicyViolation("Only approved UTF-8 text types may be created or replaced")
        if not isinstance(content, str) or "\x00" in content:
            raise BrokerPolicyViolation("content must be UTF-8 text without NUL characters")
        encoded = content.encode("utf-8")
        if len(encoded) > MAX_TEXT_BYTES:
            raise BrokerPolicyViolation(f"Text content exceeds {MAX_TEXT_BYTES} bytes")
        return content, encoded

    @staticmethod
    def _validate_file_size(path: Path) -> int:
        size = path.stat(follow_symlinks=False).st_size
        if size > MAX_SINGLE_FILE_BYTES:
            raise BrokerPolicyViolation(
                f"File exceeds the v0.8 single-file limit of {MAX_SINGLE_FILE_BYTES} bytes"
            )
        return size

    def _normalize(self, requested: dict[str, object], planned: frozenset[Path] = frozenset()) -> dict[str, object]:
        if not isinstance(requested, dict):
            raise BrokerPolicyViolation("Every operator action must be an object")
        kind = self._text(requested.get("kind"), "kind").strip().casefold()
        if kind in {"create_text", "replace_text"}:
            self._require_exact_keys(requested, {"kind", "root_id", "relative_path", "content"})
            capability = kind
            root_id = self._text(requested["root_id"], "root_id")
            relative = self._text(requested["relative_path"], "relative_path")
            record, view = self.permissions.require(root_id, capability)
            path = (
                view.resolve_new_target(relative)
                if kind == "create_text"
                else view.resolve(relative, require_file=True)
            )
            content, encoded = self._validate_text(path, requested["content"])
            normalized: dict[str, object] = {
                "kind": kind,
                "root_id": root_id,
                "root_path": str(record.path),
                "relative_path": self._canonical_relative(record, path),
                "content": content,
                "content_bytes": len(encoded),
                "content_sha256": sha256_bytes(encoded),
            }
            if kind == "replace_text":
                current = path.read_bytes()
                if len(current) > MAX_TEXT_BYTES or b"\x00" in current:
                    raise BrokerPolicyViolation("Existing target is not an approved small text file")
                try:
                    current.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise BrokerPolicyViolation("Existing target is not valid UTF-8 text") from exc
                normalized["source_snapshot"] = file_snapshot(path)
            return normalized

        if kind in {"copy", "move"}:
            self._require_exact_keys(
                requested,
                {
                    "kind",
                    "source_root_id",
                    "source_relative_path",
                    "destination_root_id",
                    "destination_relative_path",
                },
            )
            source_root_id = self._text(requested["source_root_id"], "source_root_id")
            destination_root_id = self._text(
                requested["destination_root_id"], "destination_root_id"
            )
            source_record, source_view = self.permissions.require(source_root_id, kind)
            destination_record, destination_view = self.permissions.require(
                destination_root_id, kind
            )
            source = source_view.resolve(
                self._text(requested["source_relative_path"], "source_relative_path"),
                require_file=True,
            )
            destination = destination_view.resolve_new_target(
                self._text(
                    requested["destination_relative_path"], "destination_relative_path"
                ), planned_parents=planned
            )
            size = self._validate_file_size(source)
            existing_parent = destination.parent
            while existing_parent in planned:
                existing_parent = existing_parent.parent
            if kind == "move" and source.stat().st_dev != existing_parent.stat().st_dev:
                raise BrokerPolicyViolation(
                    "Atomic move requires source and destination on the same filesystem; use copy first"
                )
            return {
                "kind": kind,
                "source_root_id": source_root_id,
                "source_root_path": str(source_record.path),
                "source_relative_path": self._canonical_relative(source_record, source),
                "destination_root_id": destination_root_id,
                "destination_root_path": str(destination_record.path),
                "destination_relative_path": self._canonical_relative(
                    destination_record, destination
                ),
                "source_snapshot": file_snapshot(source),
                "size_bytes": size,
            }

        if kind == "rename":
            self._require_exact_keys(
                requested,
                {"kind", "root_id", "source_relative_path", "destination_relative_path"},
            )
            root_id = self._text(requested["root_id"], "root_id")
            record, view = self.permissions.require(root_id, "rename")
            source = view.resolve(
                self._text(requested["source_relative_path"], "source_relative_path"),
                require_file=True,
            )
            destination = view.resolve_new_target(
                self._text(
                    requested["destination_relative_path"], "destination_relative_path"
                ), planned_parents=planned
            )
            size = self._validate_file_size(source)
            return {
                "kind": kind,
                "root_id": root_id,
                "root_path": str(record.path),
                "source_relative_path": self._canonical_relative(record, source),
                "destination_relative_path": self._canonical_relative(record, destination),
                "source_snapshot": file_snapshot(source),
                "size_bytes": size,
            }

        if kind == "mkdir":
            self._require_exact_keys(requested, {"kind", "root_id", "relative_path"})
            root_id = self._text(requested["root_id"], "root_id")
            record, view = self.permissions.require(root_id, "mkdir")
            path = view.resolve_new_target(
                self._text(requested["relative_path"], "relative_path")
            )
            return {
                "kind": kind,
                "root_id": root_id,
                "root_path": str(record.path),
                "relative_path": self._canonical_relative(record, path),
            }

        if kind == "quarantine":
            self._require_exact_keys(requested, {"kind", "root_id", "relative_path"})
            root_id = self._text(requested["root_id"], "root_id")
            record, view = self.permissions.require(root_id, "quarantine")
            path = view.resolve(
                self._text(requested["relative_path"], "relative_path"), require_file=True
            )
            size = self._validate_file_size(path)
            return {
                "kind": kind,
                "root_id": root_id,
                "root_path": str(record.path),
                "relative_path": self._canonical_relative(record, path),
                "source_snapshot": file_snapshot(path),
                "size_bytes": size,
            }
        raise BrokerPolicyViolation(f"Unsupported operator action: {kind}")

    @staticmethod
    def _public_action(action: dict[str, object]) -> dict[str, object]:
        result = dict(action)
        content = result.pop("content", None)
        result.pop("source_snapshot", None)
        if isinstance(content, str):
            result["content_preview"] = content[:160]
        return result

    @staticmethod
    def _summary(action: dict[str, object]) -> str:
        kind = str(action["kind"])
        if kind in {"create_text", "replace_text"}:
            verb = "Create" if kind == "create_text" else "Replace"
            return (
                f"{verb} '{action['relative_path']}' in approved root '{action['root_id']}' "
                f"({action['content_bytes']} UTF-8 bytes)."
            )
        if kind in {"copy", "move"}:
            return (
                f"{kind.title()} '{action['source_relative_path']}' from root "
                f"'{action['source_root_id']}' to '{action['destination_relative_path']}' "
                f"in root '{action['destination_root_id']}' ({action['size_bytes']} bytes)."
            )
        if kind == "rename":
            return (
                f"Rename '{action['source_relative_path']}' to "
                f"'{action['destination_relative_path']}' in root '{action['root_id']}'."
            )
        if kind == "mkdir":
            return f"Create directory '{action['relative_path']}' in root '{action['root_id']}'."
        return (
            f"Move '{action['relative_path']}' from root '{action['root_id']}' into Cypher "
            "quarantine. Undo remains available."
        )

    def public_plan(self, plan: OperatorPlan) -> dict[str, object]:
        return {
            "plan_id": plan.plan_id,
            "mode": "approval-gated-real-folder-operator",
            "status": plan.status,
            "item_count": len(plan.actions),
            "actions": [self._public_action(action) for action in plan.actions],
            "human_summary": [self._summary(action) for action in plan.actions],
            "fingerprint": plan.fingerprint,
            "approval_code": plan.fingerprint[-8:],
            "review_expires_at": plan.expires_at,
            "execution_expires_at": plan.approved_expires_at,
            "operation_id": plan.operation_id,
            "safety": {
                "ambient_access": False,
                "overwrite_allowed": False,
                "permanent_delete": False,
                "batch_atomic_rollback": True,
                "postcondition_verification": True,
                "approval": "one exact fingerprint",
                "content_state_protection": "Windows current-user DPAPI",
            },
        }

    def propose(self, requested_actions: list[dict[str, object]]) -> dict[str, object]:
        if not isinstance(requested_actions, list) or not requested_actions:
            raise BrokerPolicyViolation("actions must be a non-empty array")
        if len(requested_actions) > MAX_OPERATOR_ITEMS:
            raise BrokerPolicyViolation(
                f"Operator plans may contain at most {MAX_OPERATOR_ITEMS} actions"
            )
        actions = []
        planned: set[Path] = set()
        for requested in requested_actions:
            action = self._normalize(requested, frozenset(planned))
            actions.append(action)
            if action["kind"] == "mkdir":
                directory = Path(str(action["root_path"])) / str(action["relative_path"])
                if directory in planned:
                    raise BrokerPolicyViolation("Duplicate directory in operator plan")
                planned.add(directory)
        total_bytes = sum(
            int(action.get("size_bytes") or action.get("content_bytes") or 0)
            for action in actions
        )
        if total_bytes > MAX_BATCH_BYTES:
            raise BrokerPolicyViolation(
                f"Operator batch exceeds the {MAX_BATCH_BYTES}-byte limit"
            )
        plan = self.state.create_plan(actions)
        self.permissions.audit.record(
            "operator_propose_plan",
            "[operator-plan]",
            True,
            plan_id=plan.plan_id,
            item_count=len(actions),
            total_bytes=total_bytes,
        )
        return self.public_plan(plan)

    def get_plan(self, plan_id: str) -> dict[str, object]:
        return self.public_plan(self.state.get_plan(plan_id))

    def human_review_plan(self, plan_id: str) -> dict[str, object]:
        """Return the exact protected proposal for human review (native panel or CLI)."""
        plan = self.state.get_plan(plan_id)
        return {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "created_at": plan.created_at,
            "review_expires_at": plan.expires_at,
            "execution_expires_at": plan.approved_expires_at,
            "fingerprint": plan.fingerprint,
            "approval_code": plan.fingerprint[-8:],
            "actions": plan.actions,
            "safety": self.public_plan(plan)["safety"],
        }

    def _view_for(
        self, action: dict[str, object], prefix: str, capability: str
    ) -> tuple[PermissionRoot, ReadOnlyCapabilityBroker]:
        key = f"{prefix}_root_id" if prefix else "root_id"
        path_key = f"{prefix}_root_path" if prefix else "root_path"
        record, view = self.permissions.require(str(action[key]), capability)
        if str(record.path) != action[path_key]:
            raise BrokerPolicyViolation("Permission root changed after proposal")
        return record, view

    @staticmethod
    def _assert_snapshot(path: Path, expected: object) -> None:
        if not isinstance(expected, dict) or file_snapshot(path) != expected:
            raise BrokerPolicyViolation("Source changed after proposal; create a new plan")

    def _prepare_undo(
        self, action: dict[str, object], operation_id: str, index: int
    ) -> dict[str, object]:
        kind = str(action["kind"])
        if kind in {"create_text", "copy"}:
            expected = (
                action["content_sha256"]
                if kind == "create_text"
                else action["source_snapshot"]["sha256"]
            )
            if kind == "create_text":
                _record, view = self._view_for(action, "", "create_text")
                target = view.resolve_new_target(str(action["relative_path"]))
            else:
                _record, view = self._view_for(action, "destination", "copy")
                target = view.resolve_new_target(str(action["destination_relative_path"]))
            staging = target.parent / f".cypher-stage-{operation_id}-{index:03d}.tmp"
            if staging.exists() or staging.is_symlink():
                raise BrokerPolicyViolation("Operator staging path already exists")
            return {
                "kind": "remove_created_file",
                "action": action,
                "expected_sha256": expected,
                "staging_path": str(staging),
            }
        if kind == "replace_text":
            _record, view = self._view_for(action, "", "replace_text")
            path = view.resolve(str(action["relative_path"]), require_file=True)
            self._assert_snapshot(path, action["source_snapshot"])
            old = path.read_bytes()
            return {
                "kind": "restore_replaced_text",
                "action": action,
                "old_base64": base64.b64encode(old).decode("ascii"),
                "old_sha256": sha256_bytes(old),
                "expected_new_sha256": action["content_sha256"],
            }
        if kind == "mkdir":
            return {"kind": "remove_created_directory", "action": action}
        if kind in {"move", "rename"}:
            return {"kind": "move_back", "action": action}
        if kind == "quarantine":
            quarantine = self._ensure_quarantine_root() / operation_id / f"{index:03d}" / Path(
                str(action["relative_path"])
            ).name
            return {
                "kind": "restore_quarantined_file",
                "action": action,
                "quarantine_path": str(quarantine),
            }
        raise BrokerPolicyViolation(f"Unsupported operator action: {kind}")

    def _execute(self, action: dict[str, object], undo: dict[str, object]) -> None:
        kind = str(action["kind"])
        if kind == "create_text":
            _record, view = self._view_for(action, "", "create_text")
            target = view.resolve_new_target(str(action["relative_path"]))
            data = str(action["content"]).encode("utf-8")
            staging = Path(str(undo["staging_path"]))
            try:
                with staging.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                if sha256_file(staging) != action["content_sha256"]:
                    raise BrokerPolicyViolation("Staged text hash mismatch")
                os.link(staging, target)
                staging.unlink()
            except Exception:
                if staging.exists() and not ReadOnlyCapabilityBroker._is_reparse_point(staging):
                    staging.unlink()
                raise
            return
        if kind == "replace_text":
            _record, view = self._view_for(action, "", "replace_text")
            target = view.resolve(str(action["relative_path"]), require_file=True)
            self._assert_snapshot(target, action["source_snapshot"])
            data = str(action["content"]).encode("utf-8")
            temporary = target.with_name(f".{target.name}.cypher-{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
            finally:
                if temporary.exists():
                    temporary.unlink()
            return
        if kind == "copy":
            _source_record, source_view = self._view_for(action, "source", "copy")
            _destination_record, destination_view = self._view_for(
                action, "destination", "copy"
            )
            source = source_view.resolve(str(action["source_relative_path"]), require_file=True)
            self._assert_snapshot(source, action["source_snapshot"])
            target = destination_view.resolve_new_target(
                str(action["destination_relative_path"])
            )
            staging = Path(str(undo["staging_path"]))
            try:
                with source.open("rb") as input_stream, staging.open("xb") as output_stream:
                    while True:
                        chunk = input_stream.read(HASH_CHUNK_BYTES)
                        if not chunk:
                            break
                        output_stream.write(chunk)
                    output_stream.flush()
                    os.fsync(output_stream.fileno())
                if sha256_file(staging) != action["source_snapshot"]["sha256"]:
                    raise BrokerPolicyViolation("Staged copy hash mismatch")
                os.link(staging, target)
                staging.unlink()
            except Exception:
                if staging.exists() and not ReadOnlyCapabilityBroker._is_reparse_point(staging):
                    staging.unlink()
                raise
            return
        if kind == "move":
            _source_record, source_view = self._view_for(action, "source", "move")
            _destination_record, destination_view = self._view_for(
                action, "destination", "move"
            )
            source = source_view.resolve(str(action["source_relative_path"]), require_file=True)
            self._assert_snapshot(source, action["source_snapshot"])
            destination = destination_view.resolve_new_target(
                str(action["destination_relative_path"])
            )
            source.rename(destination)
            return
        if kind == "rename":
            _record, view = self._view_for(action, "", "rename")
            source = view.resolve(str(action["source_relative_path"]), require_file=True)
            self._assert_snapshot(source, action["source_snapshot"])
            destination = view.resolve_new_target(str(action["destination_relative_path"]))
            source.rename(destination)
            return
        if kind == "mkdir":
            _record, view = self._view_for(action, "", "mkdir")
            view.resolve_new_target(str(action["relative_path"])).mkdir()
            return
        if kind == "quarantine":
            _record, view = self._view_for(action, "", "quarantine")
            source = view.resolve(str(action["relative_path"]), require_file=True)
            self._assert_snapshot(source, action["source_snapshot"])
            quarantine = Path(str(undo["quarantine_path"]))
            quarantine.parent.mkdir(parents=True, exist_ok=False)
            if source.stat().st_dev == quarantine.parent.stat().st_dev:
                source.rename(quarantine)
            else:
                try:
                    with source.open("rb") as input_stream, quarantine.open("xb") as output_stream:
                        while True:
                            chunk = input_stream.read(HASH_CHUNK_BYTES)
                            if not chunk:
                                break
                            output_stream.write(chunk)
                        output_stream.flush()
                        os.fsync(output_stream.fileno())
                    if sha256_file(quarantine) != action["source_snapshot"]["sha256"]:
                        raise BrokerPolicyViolation("Quarantine copy hash mismatch")
                    source.unlink()
                except Exception:
                    if quarantine.exists() and source.exists():
                        quarantine.unlink()
                    raise
            return
        raise BrokerPolicyViolation(f"Unsupported operator action: {kind}")

    def _verify(self, action: dict[str, object], undo: dict[str, object]) -> dict[str, object]:
        kind = str(action["kind"])
        if kind in {"create_text", "replace_text"}:
            _record, view = self._view_for(action, "", kind)
            target = view.resolve(str(action["relative_path"]), require_file=True)
            expected = str(action["content_sha256"])
            actual = sha256_file(target)
            if actual != expected:
                raise BrokerPolicyViolation("Text action postcondition hash mismatch")
            return {"verified": True, "kind": kind, "sha256": actual}
        if kind == "copy":
            _record, view = self._view_for(action, "destination", "copy")
            target = view.resolve(str(action["destination_relative_path"]), require_file=True)
            actual = sha256_file(target)
            expected = str(action["source_snapshot"]["sha256"])
            if actual != expected:
                raise BrokerPolicyViolation("Copy postcondition hash mismatch")
            return {"verified": True, "kind": kind, "sha256": actual}
        if kind in {"move", "rename"}:
            capability = kind
            if kind == "move":
                _source_record, source_view = self._view_for(action, "source", capability)
                _destination_record, destination_view = self._view_for(
                    action, "destination", capability
                )
            else:
                _record, source_view = self._view_for(action, "", capability)
                destination_view = source_view
            source_relative = str(action["source_relative_path"])
            destination_relative = str(action["destination_relative_path"])
            try:
                source_view.resolve(source_relative)
            except BrokerPolicyViolation:
                pass
            else:
                raise BrokerPolicyViolation("Move source still exists after execution")
            destination = destination_view.resolve(destination_relative, require_file=True)
            actual = sha256_file(destination)
            expected = str(action["source_snapshot"]["sha256"])
            if actual != expected:
                raise BrokerPolicyViolation("Move postcondition hash mismatch")
            return {"verified": True, "kind": kind, "sha256": actual}
        if kind == "mkdir":
            _record, view = self._view_for(action, "", "mkdir")
            view.resolve(str(action["relative_path"]), require_dir=True)
            return {"verified": True, "kind": kind}
        if kind == "quarantine":
            _record, view = self._view_for(action, "", "quarantine")
            try:
                view.resolve(str(action["relative_path"]))
            except BrokerPolicyViolation:
                pass
            else:
                raise BrokerPolicyViolation("Quarantined source still exists")
            quarantine = Path(str(undo["quarantine_path"]))
            if not quarantine.is_file() or sha256_file(quarantine) != action["source_snapshot"]["sha256"]:
                raise BrokerPolicyViolation("Quarantine postcondition hash mismatch")
            return {"verified": True, "kind": kind, "sha256": sha256_file(quarantine)}
        raise BrokerPolicyViolation(f"Unsupported operator verification: {kind}")

    def _undo(self, undo: dict[str, object]) -> None:
        kind = str(undo["kind"])
        action = undo.get("action")
        if not isinstance(action, dict):
            raise BrokerPolicyViolation("Recovery action is invalid")
        action_kind = str(action["kind"])
        if kind == "remove_created_file":
            if action_kind == "create_text":
                _record, view = self._view_for(action, "", "create_text")
                relative = str(action["relative_path"])
            else:
                _record, view = self._view_for(action, "destination", "copy")
                relative = str(action["destination_relative_path"])
            staging_value = undo.get("staging_path")
            if isinstance(staging_value, str):
                staging = Path(staging_value)
                if staging.exists():
                    if staging.is_file() and not ReadOnlyCapabilityBroker._is_reparse_point(
                        staging
                    ):
                        staging.unlink()
                    else:
                        raise BrokerPolicyViolation("Operator staging path became unsafe")
            try:
                path = view.resolve(relative, require_file=True)
            except BrokerPolicyViolation:
                return
            if sha256_file(path) != undo["expected_sha256"]:
                raise BrokerPolicyViolation("Created file changed; refusing rollback deletion")
            path.unlink()
            return
        if kind == "restore_replaced_text":
            _record, view = self._view_for(action, "", "replace_text")
            path = view.resolve(str(action["relative_path"]), require_file=True)
            current = sha256_file(path)
            if current == undo["old_sha256"]:
                return
            if current != undo["expected_new_sha256"]:
                raise BrokerPolicyViolation("Replaced file changed; refusing rollback overwrite")
            old = base64.b64decode(str(undo["old_base64"]), validate=True)
            temporary = path.with_name(f".{path.name}.cypher-undo-{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(old)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
            finally:
                if temporary.exists():
                    temporary.unlink()
            return
        if kind == "remove_created_directory":
            _record, view = self._view_for(action, "", "mkdir")
            try:
                path = view.resolve(str(action["relative_path"]), require_dir=True)
            except BrokerPolicyViolation:
                return
            path.rmdir()
            return
        if kind == "move_back":
            if action_kind == "move":
                _source_record, source_view = self._view_for(action, "source", "move")
                _destination_record, destination_view = self._view_for(
                    action, "destination", "move"
                )
            else:
                _record, source_view = self._view_for(action, "", "rename")
                destination_view = source_view
            source_relative = str(action["source_relative_path"])
            destination_relative = str(action["destination_relative_path"])
            source_exists = True
            destination_exists = True
            try:
                source = source_view.resolve(source_relative, require_file=True)
            except BrokerPolicyViolation:
                source_exists = False
                source = source_view.resolve_new_target(source_relative)
            try:
                destination = destination_view.resolve(
                    destination_relative, require_file=True
                )
            except BrokerPolicyViolation:
                destination_exists = False
            if source_exists and not destination_exists:
                return
            if source_exists or not destination_exists:
                raise BrokerPolicyViolation("Move state is ambiguous; manual recovery required")
            if sha256_file(destination) != action["source_snapshot"]["sha256"]:
                raise BrokerPolicyViolation("Moved file changed; refusing rollback overwrite")
            destination.rename(source)
            return
        if kind == "restore_quarantined_file":
            _record, view = self._view_for(action, "", "quarantine")
            relative = str(action["relative_path"])
            quarantine = Path(str(undo["quarantine_path"]))
            try:
                source = view.resolve(relative, require_file=True)
                source_exists = True
            except BrokerPolicyViolation:
                source = view.resolve_new_target(relative)
                source_exists = False
            if source_exists and quarantine.is_file():
                self._assert_snapshot(source, action["source_snapshot"])
                if ReadOnlyCapabilityBroker._is_reparse_point(quarantine):
                    raise BrokerPolicyViolation("Quarantine recovery path became unsafe")
                quarantine.unlink()
                return
            if source_exists and not quarantine.exists():
                return
            if source_exists or not quarantine.is_file():
                raise BrokerPolicyViolation("Quarantine state is ambiguous; manual recovery required")
            if sha256_file(quarantine) != action["source_snapshot"]["sha256"]:
                raise BrokerPolicyViolation("Quarantined file changed; refusing restore")
            if quarantine.stat().st_dev == source.parent.stat().st_dev:
                quarantine.rename(source)
            else:
                try:
                    with quarantine.open("rb") as input_stream, source.open("xb") as output_stream:
                        while True:
                            chunk = input_stream.read(HASH_CHUNK_BYTES)
                            if not chunk:
                                break
                            output_stream.write(chunk)
                        output_stream.flush()
                        os.fsync(output_stream.fileno())
                    if sha256_file(source) != action["source_snapshot"]["sha256"]:
                        raise BrokerPolicyViolation("Restored quarantine copy hash mismatch")
                    quarantine.unlink()
                except Exception:
                    if source.exists() and quarantine.exists():
                        source.unlink()
                    raise
            return
        raise BrokerPolicyViolation(f"Unsupported recovery kind: {kind}")

    def _rollback_operation(self, plan_id: str, operation_id: str, status: str,
                            cancelled: Callable[[], bool] | None = None) -> None:
        failure: Exception | None = None
        for row in reversed(self.state.operation_steps(operation_id)):
            if row["status"] not in {"prepared", "performed", "verified"}:
                continue
            try:
                if cancelled is not None and cancelled():
                    raise OperatorCancelled("Stop requested during reversal; review recovery to continue")
                self._undo(self.state.step_undo(row))
                self.state.mark_step_rolled_back(operation_id, int(row["step_index"]))
            except Exception as exc:  # preserve evidence and stop claiming recovery
                failure = exc
                break
        final_status = "recovery_required" if failure is not None else status
        self.state.set_operation_status(operation_id, plan_id, final_status)
        if failure is not None:
            raise BrokerPolicyViolation(
                f"Automatic rollback could not finish safely: {failure}"
            ) from failure

    @exclusive_execution
    def apply(self, plan_id: str, *, cancelled: Callable[[], bool] | None = None,
              progress: Callable[[int, int], None] | None = None) -> dict[str, object]:
        def check_stop() -> None:
            if cancelled is not None and cancelled():
                raise OperatorCancelled("Stop requested; later actions were not started")
        if self.state.incomplete_operations():
            raise BrokerPolicyViolation('Interrupted file changes require recovery before another apply')
        plan, operation_id = self.state.claim(plan_id)
        try:
            for index, action in enumerate(plan.actions):
                check_stop()
                undo = self._prepare_undo(action, operation_id, index)
                self.state.prepare_step(operation_id, index, undo)
                self._execute(action, undo)
                self.state.mark_step_performed(operation_id, index)
                verification = self._verify(action, undo)
                self.state.mark_step_verified(operation_id, index, verification)
                if progress is not None:
                    progress(index + 1, len(plan.actions))
            check_stop()
            self.state.finish(plan.plan_id, operation_id)
        except OperatorCancelled:
            self._rollback_operation(plan.plan_id, operation_id, "cancelled_rolled_back")
            raise
        except Exception:
            self._rollback_operation(plan.plan_id, operation_id, "failed_rolled_back")
            raise
        self.permissions.audit.record(
            "operator_apply_approved_plan",
            "[operator-plan]",
            True,
            plan_id=plan.plan_id,
            operation_id=operation_id,
            item_count=len(plan.actions),
        )
        return {
            "status": "executed",
            "plan_id": plan.plan_id,
            "operation_id": operation_id,
            "item_count": len(plan.actions),
            "verified_items": len(plan.actions),
            "undo_available": True,
        }

    def operation_status(self, operation_id: str) -> dict[str, object]:
        operation = self.state.operation(operation_id)
        rows = self.state.operation_steps(operation_id)
        return {
            "operation_id": operation_id,
            "plan_id": operation["plan_id"],
            "status": operation["status"],
            "item_count": operation["item_count"],
            "steps": [
                {
                    "step": row["step_index"] + 1,
                    "kind": row["kind"],
                    "status": row["status"],
                    "verified": row["verification_json"] is not None,
                }
                for row in rows
            ],
        }

    @exclusive_execution
    def undo_operation(self, operation_id: str, *, cancelled: Callable[[], bool] | None = None) -> dict[str, object]:
        operation = self.state.operation(operation_id)
        if operation["status"] != "executed":
            raise BrokerPolicyViolation(
                f"Operation is not eligible for undo: {operation['status']}"
            )
        if cancelled is not None and cancelled():
            raise OperatorCancelled("Undo cancelled before any reverse action")
        self.state.begin_undo(operation_id, operation["plan_id"])
        self._rollback_operation(operation["plan_id"], operation_id, "undone", cancelled)
        self.permissions.audit.record(
            "operator_undo",
            "[operator-operation]",
            True,
            operation_id=operation_id,
            item_count=operation["item_count"],
        )
        return {"status": "undone", "operation_id": operation_id}

    @exclusive_execution
    def reconcile_incomplete(self, *, cancelled: Callable[[], bool] | None = None) -> dict[str, object]:
        recovered: list[str] = []
        failed: list[str] = []
        for operation in self.state.incomplete_operations():
            try:
                recovered_status = (
                    "undone_after_restart"
                    if operation["status"] == "undoing"
                    else "restart_recovered"
                )
                self._rollback_operation(
                    operation["plan_id"], operation["operation_id"], recovered_status, cancelled
                )
                recovered.append(operation["operation_id"])
            except BrokerPolicyViolation:
                failed.append(operation["operation_id"])
        self.permissions.audit.record(
            "operator_restart_reconcile",
            "[operator-operation]",
            not failed,
            recovered=len(recovered),
            recovery_required=len(failed),
        )
        return {
            "recovered_operations": recovered,
            "recovery_required": failed,
            "safe_to_start": not failed,
        }
