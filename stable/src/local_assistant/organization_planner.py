from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
from typing import Iterator
import unicodedata
import uuid

from .capability_broker import (
    BrokerPolicyViolation,
    MetadataAuditLog,
    ReadOnlyCapabilityBroker,
)
from .inventory_broker import InventoryRoot, MetadataInventoryBroker


ORGANIZATION_PLAN_VERSION = 1
ORGANIZATION_PLAN_TTL_MINUTES = 60
MAX_PLAN_ITEMS = 50
MAX_REASON_BYTES = 500
MAX_RELATIVE_PATH_CHARS = 1024
MAX_ACTIVE_PROPOSED_PLANS = 20
MAX_PROPOSALS_PER_TEN_MINUTES = 10
MAX_STORED_PLANS = 1000
WINDOWS_RESERVED_NAME = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.IGNORECASE
)
WINDOWS_INVALID_CHARS = set('<>:"|?*')


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def calculate_plan_fingerprint(
    plan_id: str,
    source_root_id: str,
    source_root_path: str,
    destination_root_id: str,
    destination_root_path: str,
    items: list[dict[str, object]],
    expires_at: str,
) -> str:
    payload = {
        "version": ORGANIZATION_PLAN_VERSION,
        "plan_id": plan_id,
        "source_root_id": source_root_id,
        "source_root_path": source_root_path,
        "destination_root_id": destination_root_id,
        "destination_root_path": destination_root_path,
        "items": items,
        "expires_at": expires_at,
    }
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OrganizationPlan:
    plan_id: str
    source_root_id: str
    source_root_path: str
    destination_root_id: str
    destination_root_path: str
    items: list[dict[str, object]]
    fingerprint: str
    status: str
    created_at: str
    expires_at: str
    reviewed_at: str | None = None


class OrganizationPlanStore:
    """Local planning state. It has no filesystem execution method."""

    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS organization_plans (
                    plan_id TEXT PRIMARY KEY,
                    version INTEGER NOT NULL,
                    source_root_id TEXT NOT NULL,
                    source_root_path TEXT NOT NULL,
                    destination_root_id TEXT NOT NULL,
                    destination_root_path TEXT NOT NULL,
                    items_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    reviewed_at TEXT
                )
                """
            )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> OrganizationPlan:
        if row["version"] != ORGANIZATION_PLAN_VERSION:
            raise BrokerPolicyViolation("Organization plan version is unsupported")
        try:
            items = json.loads(row["items_json"])
        except json.JSONDecodeError as exc:
            raise BrokerPolicyViolation("Organization plan data is invalid") from exc
        if not isinstance(items, list):
            raise BrokerPolicyViolation("Organization plan items are invalid")
        if row["status"] not in {"proposed", "reviewed", "rejected", "expired"}:
            raise BrokerPolicyViolation("Organization plan status is invalid")
        try:
            datetime.fromisoformat(row["created_at"])
            datetime.fromisoformat(row["expires_at"])
        except (TypeError, ValueError) as exc:
            raise BrokerPolicyViolation("Organization plan timestamps are invalid") from exc
        expected_fingerprint = calculate_plan_fingerprint(
            row["plan_id"],
            row["source_root_id"],
            row["source_root_path"],
            row["destination_root_id"],
            row["destination_root_path"],
            items,
            row["expires_at"],
        )
        if not isinstance(row["fingerprint"], str) or not hmac.compare_digest(
            row["fingerprint"], expected_fingerprint
        ):
            raise BrokerPolicyViolation(
                "Organization plan fingerprint does not match stored plan data"
            )
        return OrganizationPlan(
            plan_id=row["plan_id"],
            source_root_id=row["source_root_id"],
            source_root_path=row["source_root_path"],
            destination_root_id=row["destination_root_id"],
            destination_root_path=row["destination_root_path"],
            items=items,
            fingerprint=row["fingerprint"],
            status=row["status"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            reviewed_at=row["reviewed_at"],
        )

    def create(
        self,
        source: InventoryRoot,
        destination: InventoryRoot,
        items: list[dict[str, object]],
    ) -> OrganizationPlan:
        plan_id = str(uuid.uuid4())
        created = utc_now()
        expires = created + timedelta(minutes=ORGANIZATION_PLAN_TTL_MINUTES)
        fingerprint = calculate_plan_fingerprint(
            plan_id,
            source.root_id,
            str(source.path),
            destination.root_id,
            str(destination.path),
            items,
            expires.isoformat(),
        )
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                UPDATE organization_plans SET status='expired'
                WHERE status IN ('proposed', 'reviewed') AND expires_at <= ?
                """,
                (created.isoformat(),),
            )
            total = connection.execute(
                "SELECT COUNT(*) FROM organization_plans"
            ).fetchone()[0]
            active = connection.execute(
                "SELECT COUNT(*) FROM organization_plans WHERE status='proposed'"
            ).fetchone()[0]
            recent_cutoff = (created - timedelta(minutes=10)).isoformat()
            recent = connection.execute(
                "SELECT COUNT(*) FROM organization_plans WHERE created_at >= ?",
                (recent_cutoff,),
            ).fetchone()[0]
            if total >= MAX_STORED_PLANS:
                raise BrokerPolicyViolation(
                    "Organization plan storage limit reached; stop and review local plan state"
                )
            if active >= MAX_ACTIVE_PROPOSED_PLANS:
                raise BrokerPolicyViolation(
                    "Too many active dry-run plans; review or reject existing plans first"
                )
            if recent >= MAX_PROPOSALS_PER_TEN_MINUTES:
                raise BrokerPolicyViolation(
                    "Dry-run proposal rate limit reached; wait before creating another plan"
                )
            connection.execute(
                """
                INSERT INTO organization_plans
                (plan_id, version, source_root_id, source_root_path,
                 destination_root_id, destination_root_path, items_json,
                 fingerprint, status, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'proposed', ?, ?)
                """,
                (
                    plan_id,
                    ORGANIZATION_PLAN_VERSION,
                    source.root_id,
                    str(source.path),
                    destination.root_id,
                    str(destination.path),
                    canonical_json(items),
                    fingerprint,
                    created.isoformat(),
                    expires.isoformat(),
                ),
            )
        return self.get(plan_id)

    def get(self, plan_id: str) -> OrganizationPlan:
        if not isinstance(plan_id, str) or not plan_id:
            raise BrokerPolicyViolation("plan_id must be non-empty text")
        with self._managed_connection() as connection:
            row = connection.execute(
                "SELECT * FROM organization_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
        if row is None:
            raise BrokerPolicyViolation(f"Unknown organization plan: {plan_id}")
        return self._from_row(row)

    def list(self, limit: int = 20) -> list[OrganizationPlan]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 100:
            raise BrokerPolicyViolation("Plan list limit must be from 1 to 100")
        with self._managed_connection() as connection:
            rows = connection.execute(
                "SELECT * FROM organization_plans ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def mark_expired(self, plan_id: str) -> OrganizationPlan:
        with self._managed_connection() as connection:
            connection.execute(
                """
                UPDATE organization_plans SET status='expired'
                WHERE plan_id=? AND status IN ('proposed', 'reviewed')
                """,
                (plan_id,),
            )
        return self.get(plan_id)

    def mark_reviewed(self, plan_id: str, fingerprint: str) -> OrganizationPlan:
        now = utc_now()
        rejection: str | None = None
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM organization_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown organization plan: {plan_id}")
            plan = self._from_row(row)
            if plan.status != "proposed":
                raise BrokerPolicyViolation(f"Plan is not awaiting review: {plan.status}")
            if datetime.fromisoformat(plan.expires_at) <= now:
                connection.execute(
                    "UPDATE organization_plans SET status='expired' WHERE plan_id=?",
                    (plan_id,),
                )
                rejection = "Organization plan expired; create a new proposal"
            elif fingerprint != plan.fingerprint:
                raise BrokerPolicyViolation("Organization plan fingerprint mismatch")
            else:
                connection.execute(
                    """
                    UPDATE organization_plans SET status='reviewed', reviewed_at=?
                    WHERE plan_id=?
                    """,
                    (now.isoformat(), plan_id),
                )
        if rejection is not None:
            raise BrokerPolicyViolation(rejection)
        return self.get(plan_id)

    def mark_rejected(self, plan_id: str, fingerprint: str) -> OrganizationPlan:
        with self._managed_connection() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM organization_plans WHERE plan_id=?", (plan_id,)
            ).fetchone()
            if row is None:
                raise BrokerPolicyViolation(f"Unknown organization plan: {plan_id}")
            plan = self._from_row(row)
            if plan.status not in {"proposed", "reviewed"}:
                raise BrokerPolicyViolation(f"Plan cannot be rejected: {plan.status}")
            if fingerprint != plan.fingerprint:
                raise BrokerPolicyViolation("Organization plan fingerprint mismatch")
            connection.execute(
                "UPDATE organization_plans SET status='rejected' WHERE plan_id=?",
                (plan_id,),
            )
        return self.get(plan_id)


class DryRunOrganizationPlanner:
    """Creates and validates metadata-bound plans; it cannot execute them."""

    def __init__(
        self,
        inventory: MetadataInventoryBroker,
        destinations: list[InventoryRoot],
        state: OrganizationPlanStore,
        audit_path: Path | None = None,
    ):
        self.inventory = inventory
        self.destinations = {item.root_id: item for item in destinations}
        self.destination_views = {
            item.root_id: ReadOnlyCapabilityBroker(item.path, None)
            for item in destinations
        }
        self.state = state
        self.audit = MetadataAuditLog(audit_path)

    @staticmethod
    def _same_path(left: Path, right: Path) -> bool:
        return os.path.normcase(str(left)) == os.path.normcase(str(right))

    @staticmethod
    def _is_within(candidate: Path, parent: Path) -> bool:
        try:
            return os.path.commonpath(
                [os.path.normcase(str(candidate)), os.path.normcase(str(parent))]
            ) == os.path.normcase(str(parent))
        except ValueError:
            return False

    def _destination(self, root_id: str) -> tuple[InventoryRoot, ReadOnlyCapabilityBroker]:
        if not isinstance(root_id, str) or root_id not in self.destinations:
            raise BrokerPolicyViolation(f"Unknown organization destination: {root_id}")
        record = self.destinations[root_id]
        if not record.path.exists() or not record.path.is_dir():
            raise BrokerPolicyViolation("Organization destination is no longer available")
        if ReadOnlyCapabilityBroker._is_reparse_point(record.path):
            raise BrokerPolicyViolation("Organization destination became a link or reparse point")
        return record, self.destination_views[root_id]

    def status(self) -> dict[str, object]:
        result = {
            "mode": "dry-run-only",
            "execution_available": False,
            "real_file_writes": False,
            "local_plan_state_writes": True,
            "content_reads": False,
            "source_inventory_roots": [
                {"root_id": item.root_id, "path": str(item.path)}
                for item in sorted(
                    self.inventory.roots.values(), key=lambda record: record.root_id
                )
            ],
            "planning_destinations": [
                {"root_id": item.root_id, "path": str(item.path)}
                for item in sorted(self.destinations.values(), key=lambda record: record.root_id)
            ],
            "limits": {
                "max_items_per_plan": MAX_PLAN_ITEMS,
                "plan_review_minutes": ORGANIZATION_PLAN_TTL_MINUTES,
                "graphic_extensions_only": True,
                "filename_preservation_required": True,
                "overwrite_allowed": False,
                "max_active_proposed_plans": MAX_ACTIVE_PROPOSED_PLANS,
                "max_proposals_per_ten_minutes": MAX_PROPOSALS_PER_TEN_MINUTES,
                "max_stored_plans": MAX_STORED_PLANS,
            },
        }
        self.audit.record(
            "organization_status",
            "[organization]",
            True,
            source_roots=len(self.inventory.roots),
            destination_roots=len(self.destinations),
        )
        return result

    @staticmethod
    def _validate_reason(value: object) -> str:
        if not isinstance(value, str):
            raise BrokerPolicyViolation("Organization reason must be text")
        reason = value.strip()
        if not reason:
            raise BrokerPolicyViolation("Organization reason cannot be empty")
        if any(
            ord(character) < 32 or unicodedata.category(character) == "Cf"
            for character in reason
        ):
            raise BrokerPolicyViolation(
                "Organization reason cannot contain control or formatting characters"
            )
        if len(reason.encode("utf-8")) > MAX_REASON_BYTES:
            raise BrokerPolicyViolation(
                f"Organization reason exceeds {MAX_REASON_BYTES} UTF-8 bytes"
            )
        return reason

    @staticmethod
    def _destination_parts(value: object) -> tuple[str, ...]:
        if not isinstance(value, str):
            raise BrokerPolicyViolation("destination_relative_path must be text")
        text = value.strip().replace("\\", "/")
        if not text or len(text) > MAX_RELATIVE_PATH_CHARS or ":" in text:
            raise BrokerPolicyViolation("Destination must be a bounded relative path")
        path = PurePosixPath(text)
        if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
            raise BrokerPolicyViolation("Destination path traversal is not allowed")
        for part in path.parts:
            if len(part) > 255 or part.endswith((" ", ".")):
                raise BrokerPolicyViolation("Destination contains an unsafe Windows name")
            if WINDOWS_RESERVED_NAME.fullmatch(part):
                raise BrokerPolicyViolation("Destination contains a reserved Windows name")
            if any(
                character in WINDOWS_INVALID_CHARS
                or ord(character) < 32
                or unicodedata.category(character) == "Cf"
                for character in part
            ):
                raise BrokerPolicyViolation("Destination contains an invalid Windows character")
            if part.startswith(".") or part.casefold() in ReadOnlyCapabilityBroker.BLOCKED_NAMES:
                raise BrokerPolicyViolation("Destination contains a protected name")
        return path.parts

    @classmethod
    def _destination_target(
        cls,
        destination: InventoryRoot,
        view: ReadOnlyCapabilityBroker,
        relative_path: object,
    ) -> tuple[Path, str]:
        parts = cls._destination_parts(relative_path)
        current = destination.path
        for index, part in enumerate(parts):
            current = current / part
            view._validate_name(current)
            if view._is_reparse_point(current):
                raise BrokerPolicyViolation(
                    "Destination path contains a link or reparse point"
                )
            if current.exists() or current.is_symlink():
                if index < len(parts) - 1 and not current.is_dir():
                    raise BrokerPolicyViolation(
                        "Destination parent is not a directory"
                    )
        try:
            current.relative_to(destination.path)
        except ValueError as exc:
            raise BrokerPolicyViolation(
                "Destination escaped the approved planning root"
            ) from exc
        return current, "/".join(parts)

    def _validate_root_relationship(
        self, source: InventoryRoot, destination: InventoryRoot
    ) -> None:
        if self._same_path(source.path, destination.path):
            raise BrokerPolicyViolation(
                "Source and destination roots must be different permissions"
            )
        if self._is_within(source.path, destination.path):
            raise BrokerPolicyViolation(
                "A planning destination cannot contain the approved source root"
            )

    def propose_graphic_plan(
        self,
        source_root_id: str,
        destination_root_id: str,
        requested_items: list[dict[str, object]],
    ) -> dict[str, object]:
        if not isinstance(requested_items, list):
            raise BrokerPolicyViolation("items must be an array")
        if not requested_items or len(requested_items) > MAX_PLAN_ITEMS:
            raise BrokerPolicyViolation(
                f"Organization plans must contain 1 to {MAX_PLAN_ITEMS} items"
            )
        source_view = self.inventory._view(source_root_id)
        source = self.inventory.roots[source_root_id]
        destination, destination_view = self._destination(destination_root_id)
        self._validate_root_relationship(source, destination)

        items: list[dict[str, object]] = []
        sources_seen: set[str] = set()
        destinations_seen: set[str] = set()
        for requested in requested_items:
            if not isinstance(requested, dict) or set(requested) != {
                "source_relative_path",
                "destination_relative_path",
                "reason",
            }:
                raise BrokerPolicyViolation(
                    "Each organization item must contain only source_relative_path, "
                    "destination_relative_path, and reason"
                )
            source_value = requested["source_relative_path"]
            if not isinstance(source_value, str):
                raise BrokerPolicyViolation("source_relative_path must be text")
            source_path = source_view.resolve(source_value, require_file=True)
            if ReadOnlyCapabilityBroker._is_reparse_point(source_path):
                raise BrokerPolicyViolation("Organization source cannot be a link")
            canonical_source = source_path.relative_to(source.path).as_posix()
            if any(
                ord(character) < 32 or unicodedata.category(character) == "Cf"
                for character in canonical_source
            ):
                raise BrokerPolicyViolation(
                    "Organization source path contains control or formatting characters"
                )
            source_key = os.path.normcase(canonical_source)
            if source_key in sources_seen:
                raise BrokerPolicyViolation("A source file may appear only once in a plan")
            if self._is_within(source_path, destination.path):
                raise BrokerPolicyViolation(
                    "A source already inside the destination root cannot be planned again"
                )

            classification = self.inventory._classify(source_path.suffix.casefold())
            if classification is None:
                raise BrokerPolicyViolation(
                    "Only extension-classified graphic candidates may be planned in v0.5"
                )
            category, confidence = classification
            destination_path, canonical_destination = self._destination_target(
                destination,
                destination_view,
                requested["destination_relative_path"],
            )
            if PurePosixPath(canonical_destination).name != source_path.name:
                raise BrokerPolicyViolation(
                    "v0.5 preserves filenames; destination basename must exactly match source"
                )
            if destination_path.exists() or destination_path.is_symlink():
                raise BrokerPolicyViolation(
                    "Destination already exists; overwrite is never planned"
                )
            destination_key = os.path.normcase(canonical_destination)
            if destination_key in destinations_seen:
                raise BrokerPolicyViolation(
                    "Two items cannot share one destination path"
                )

            info = source_path.stat(follow_symlinks=False)
            items.append(
                {
                    "source_relative_path": canonical_source,
                    "destination_relative_path": canonical_destination,
                    "reason": self._validate_reason(requested["reason"]),
                    "category": category,
                    "confidence": confidence,
                    "source_snapshot": {
                        "size_bytes": info.st_size,
                        "modified_ns": info.st_mtime_ns,
                        "modified_utc": datetime.fromtimestamp(
                            info.st_mtime, timezone.utc
                        ).isoformat(),
                        "device_id": info.st_dev,
                        "file_id": info.st_ino,
                    },
                }
            )
            sources_seen.add(source_key)
            destinations_seen.add(destination_key)

        plan = self.state.create(source, destination, items)
        self.audit.record(
            "organization_propose_graphic_plan",
            "[organization]",
            True,
            plan_id=plan.plan_id,
            source_root_id=source.root_id,
            destination_root_id=destination.root_id,
            item_count=len(items),
        )
        return self.public_plan(plan)

    @staticmethod
    def public_plan(plan: OrganizationPlan) -> dict[str, object]:
        return {
            "plan_id": plan.plan_id,
            "mode": "dry-run-only",
            "execution_available": False,
            "source_root_id": plan.source_root_id,
            "source_root_path": plan.source_root_path,
            "destination_root_id": plan.destination_root_id,
            "destination_root_path": plan.destination_root_path,
            "items": plan.items,
            "item_count": len(plan.items),
            "fingerprint": plan.fingerprint,
            "review_code": plan.fingerprint[-8:],
            "status": plan.status,
            "created_at": plan.created_at,
            "review_expires_at": plan.expires_at,
            "reviewed_at": plan.reviewed_at,
            "review_command": (
                ".\\scripts\\manage_organization_plans_windows.ps1 review "
                f"{plan.plan_id}"
            ),
            "security_note": (
                "Review records human acceptance of this dry run only. "
                "It grants no execution permission and cannot move files in v0.5."
            ),
        }

    def get_plan(self, plan_id: str) -> dict[str, object]:
        plan = self.state.get(plan_id)
        result = self.public_plan(plan)
        self.audit.record(
            "organization_get_plan",
            "[organization]",
            True,
            plan_id=plan.plan_id,
            item_count=len(plan.items),
            status=plan.status,
        )
        return result

    def validate_plan(self, plan_id: str) -> dict[str, object]:
        plan = self.state.get(plan_id)
        issues: list[dict[str, object]] = []
        if datetime.fromisoformat(plan.expires_at) <= utc_now():
            plan = self.state.mark_expired(plan.plan_id)
            issues.append({"code": "expired", "message": "Plan review window expired"})

        source = self.inventory.roots.get(plan.source_root_id)
        destination = self.destinations.get(plan.destination_root_id)
        if source is None or str(source.path) != plan.source_root_path:
            issues.append(
                {"code": "source_permission_changed", "message": "Source permission changed"}
            )
        if destination is None or str(destination.path) != plan.destination_root_path:
            issues.append(
                {
                    "code": "destination_permission_changed",
                    "message": "Destination permission changed",
                }
            )

        if source is not None and destination is not None:
            try:
                source_view = self.inventory._view(source.root_id)
                destination_record, destination_view = self._destination(
                    destination.root_id
                )
                self._validate_root_relationship(source, destination_record)
            except (BrokerPolicyViolation, OSError) as exc:
                issues.append({"code": "root_unavailable", "message": str(exc)})
            else:
                destination_keys: set[str] = set()
                for index, item in enumerate(plan.items):
                    if not isinstance(item, dict):
                        issues.append(
                            {"code": "invalid_plan_item", "item": index + 1}
                        )
                        continue
                    source_relative = item.get("source_relative_path")
                    destination_relative = item.get("destination_relative_path")
                    snapshot = item.get("source_snapshot")
                    try:
                        if not isinstance(source_relative, str) or not isinstance(
                            destination_relative, str
                        ) or not isinstance(snapshot, dict):
                            raise BrokerPolicyViolation("Stored plan item is invalid")
                        source_path = source_view.resolve(
                            source_relative, require_file=True
                        )
                        if ReadOnlyCapabilityBroker._is_reparse_point(source_path):
                            raise BrokerPolicyViolation("Source became a link")
                        info = source_path.stat(follow_symlinks=False)
                        current_snapshot = {
                            "size_bytes": info.st_size,
                            "modified_ns": info.st_mtime_ns,
                            "device_id": info.st_dev,
                            "file_id": info.st_ino,
                        }
                        expected_snapshot = {
                            key: snapshot.get(key)
                            for key in (
                                "size_bytes",
                                "modified_ns",
                                "device_id",
                                "file_id",
                            )
                        }
                        if current_snapshot != expected_snapshot:
                            raise BrokerPolicyViolation(
                                "Source metadata changed after proposal"
                            )
                        target, canonical_destination = self._destination_target(
                            destination_record,
                            destination_view,
                            destination_relative,
                        )
                        destination_key = os.path.normcase(canonical_destination)
                        if destination_key in destination_keys:
                            raise BrokerPolicyViolation(
                                "Plan contains a duplicate destination"
                            )
                        destination_keys.add(destination_key)
                        if target.exists() or target.is_symlink():
                            raise BrokerPolicyViolation(
                                "Destination appeared after proposal"
                            )
                    except (BrokerPolicyViolation, OSError) as exc:
                        issues.append(
                            {
                                "code": "item_not_ready",
                                "item": index + 1,
                                "source_relative_path": source_relative,
                                "destination_relative_path": destination_relative,
                                "message": str(exc),
                            }
                        )

        result = {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "ready_for_human_review": not issues and plan.status == "proposed",
            "still_matches_metadata": not issues,
            "execution_available": False,
            "issues": issues,
            "checked_items": len(plan.items),
            "content_read": False,
            "real_files_changed": False,
        }
        self.audit.record(
            "organization_validate_plan",
            "[organization]",
            True,
            plan_id=plan.plan_id,
            status=plan.status,
            item_count=len(plan.items),
            issue_count=len(issues),
        )
        return result
