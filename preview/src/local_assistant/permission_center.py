from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Iterable, Mapping
import uuid

from .capability_broker import (
    BrokerPolicyViolation,
    MetadataAuditLog,
    ReadOnlyCapabilityBroker,
)
from .inventory_broker import InventoryRootStore, MAX_CONFIG_BYTES, MAX_ROOTS


PERMISSION_CONFIG_VERSION = 1
SUPPORTED_CAPABILITIES = frozenset(
    {
        "metadata",
        "read_text",
        "create_text",
        "replace_text",
        "copy",
        "move",
        "rename",
        "mkdir",
        "quarantine",
    }
)


@dataclass(frozen=True)
class PermissionRoot:
    root_id: str
    path: Path
    capabilities: frozenset[str]
    added_at: str


class PermissionRootStore:
    """Human-managed capability allowlist for explicitly selected folders."""

    def __init__(
        self,
        path: Path,
        *,
        home: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ):
        self.path = path
        self._validator = InventoryRootStore(
            path.with_name(path.name + ".validation-only"),
            home=home,
            environment=environment,
        )

    @staticmethod
    def validate_capabilities(values: Iterable[str]) -> frozenset[str]:
        if isinstance(values, (str, bytes)):
            raise BrokerPolicyViolation("Capabilities must be a list, not text")
        normalized: set[str] = set()
        for value in values:
            if not isinstance(value, str):
                raise BrokerPolicyViolation("Every capability must be text")
            capability = value.strip().casefold()
            if capability not in SUPPORTED_CAPABILITIES:
                raise BrokerPolicyViolation(f"Unsupported capability: {value}")
            normalized.add(capability)
        if not normalized:
            raise BrokerPolicyViolation("At least one capability is required")
        if "metadata" not in normalized:
            normalized.add("metadata")
        return frozenset(normalized)

    def load(self) -> list[PermissionRoot]:
        if not self.path.exists():
            return []
        if ReadOnlyCapabilityBroker._is_reparse_point(self.path):
            raise BrokerPolicyViolation("Permission configuration cannot be a link")
        if self.path.stat().st_size > MAX_CONFIG_BYTES:
            raise BrokerPolicyViolation("Permission configuration is unexpectedly large")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BrokerPolicyViolation("Permission configuration is invalid") from exc
        if not isinstance(payload, dict) or set(payload) != {"version", "roots"}:
            raise BrokerPolicyViolation("Permission configuration has an unexpected structure")
        if payload["version"] != PERMISSION_CONFIG_VERSION or not isinstance(
            payload["roots"], list
        ):
            raise BrokerPolicyViolation("Permission configuration version is unsupported")
        if len(payload["roots"]) > MAX_ROOTS:
            raise BrokerPolicyViolation(f"No more than {MAX_ROOTS} permission roots are allowed")

        records: list[PermissionRoot] = []
        for item in payload["roots"]:
            if not isinstance(item, dict) or set(item) != {
                "id",
                "path",
                "capabilities",
                "added_at",
            }:
                raise BrokerPolicyViolation("Permission root record has an unexpected structure")
            root_id = InventoryRootStore.validate_root_id(item["id"])
            if not isinstance(item["path"], str) or not isinstance(
                item["capabilities"], list
            ):
                raise BrokerPolicyViolation("Permission root record contains invalid values")
            added_at = InventoryRootStore.validate_added_at(item["added_at"])
            try:
                path = self._validator.validate_root_path(Path(item["path"]))
            except OSError as exc:
                raise BrokerPolicyViolation("Permission root is no longer available") from exc
            capabilities = self.validate_capabilities(item["capabilities"])
            if any(record.root_id == root_id for record in records):
                raise BrokerPolicyViolation(f"Duplicate permission root ID: {root_id}")
            if any(
                self._validator._is_within(path, record.path)
                or self._validator._is_within(record.path, path)
                for record in records
            ):
                raise BrokerPolicyViolation("Overlapping permission roots are not allowed")
            records.append(PermissionRoot(root_id, path, capabilities, added_at))
        return sorted(records, key=lambda record: record.root_id)

    def _save(self, records: list[PermissionRoot]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": PERMISSION_CONFIG_VERSION,
            "roots": [
                {
                    "id": record.root_id,
                    "path": str(record.path),
                    "capabilities": sorted(record.capabilities),
                    "added_at": record.added_at,
                }
                for record in sorted(records, key=lambda record: record.root_id)
            ],
        }
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(payload, stream, ensure_ascii=True, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            try:
                temporary.chmod(0o600)
            except OSError:
                pass
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def add(
        self, root_id: str, path: Path, capabilities: Iterable[str]
    ) -> PermissionRoot:
        validated_id = InventoryRootStore.validate_root_id(root_id)
        validated_capabilities = self.validate_capabilities(capabilities)
        try:
            validated_path = self._validator.validate_root_path(path)
        except OSError as exc:
            raise BrokerPolicyViolation("Permission root must be an existing directory") from exc
        records = self.load()
        if any(record.root_id == validated_id for record in records):
            raise BrokerPolicyViolation(f"Permission root ID already exists: {validated_id}")
        if any(
            self._validator._is_within(validated_path, record.path)
            or self._validator._is_within(record.path, validated_path)
            for record in records
        ):
            raise BrokerPolicyViolation("Permission root overlaps an existing root")
        if len(records) >= MAX_ROOTS:
            raise BrokerPolicyViolation(f"No more than {MAX_ROOTS} permission roots are allowed")
        record = PermissionRoot(
            validated_id,
            validated_path,
            validated_capabilities,
            datetime.now(timezone.utc).isoformat(),
        )
        self._save([*records, record])
        return record

    def remove(self, root_id: str) -> PermissionRoot:
        validated_id = InventoryRootStore.validate_root_id(root_id)
        records = self.load()
        selected = next((record for record in records if record.root_id == validated_id), None)
        if selected is None:
            raise BrokerPolicyViolation(f"Unknown permission root: {validated_id}")
        self._save([record for record in records if record.root_id != validated_id])
        return selected


class PermissionCenter:
    """Runtime view of human-approved roots and their exact capability scopes."""

    def __init__(
        self,
        roots: list[PermissionRoot],
        audit_path: Path | None = None,
    ):
        self.roots = {record.root_id: record for record in roots}
        self.views = {
            record.root_id: ReadOnlyCapabilityBroker(record.path, None)
            for record in roots
        }
        self.audit = MetadataAuditLog(audit_path)

    def status(self) -> dict[str, object]:
        result = {
            "mode": "explicit-folder-capabilities",
            "ambient_access": False,
            "administrator_access": False,
            "root_count": len(self.roots),
            "roots": [
                {
                    "root_id": record.root_id,
                    "path": str(record.path),
                    "capabilities": sorted(record.capabilities),
                }
                for record in sorted(self.roots.values(), key=lambda item: item.root_id)
            ],
            "supported_capabilities": sorted(SUPPORTED_CAPABILITIES),
        }
        self.audit.record("operator_permission_status", "[permissions]", True, roots=len(self.roots))
        return result

    def require(self, root_id: str, capability: str) -> tuple[PermissionRoot, ReadOnlyCapabilityBroker]:
        if not isinstance(root_id, str) or root_id not in self.roots:
            raise BrokerPolicyViolation(f"Unknown permission root: {root_id}")
        record = self.roots[root_id]
        if capability not in record.capabilities:
            raise BrokerPolicyViolation(
                f"Root '{root_id}' does not allow capability '{capability}'"
            )
        if not record.path.exists() or not record.path.is_dir():
            raise BrokerPolicyViolation(f"Permission root is unavailable: {root_id}")
        if ReadOnlyCapabilityBroker._is_reparse_point(record.path):
            raise BrokerPolicyViolation(f"Permission root became a link: {root_id}")
        return record, self.views[root_id]

    def read_text(
        self, root_id: str, relative_path: str, max_bytes: int = 32_768
    ) -> dict[str, object]:
        record, view = self.require(root_id, "read_text")
        result = view.read_text(relative_path, max_bytes)
        result["root_id"] = root_id
        result["root_path"] = str(record.path)
        self.audit.record(
            "operator_read_text",
            "[approved-root]",
            True,
            root_id=root_id,
            bytes=result["bytes"],
        )
        return result
