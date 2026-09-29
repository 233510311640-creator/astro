from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Mapping
import uuid

from .capability_broker import (
    BrokerPolicyViolation,
    MetadataAuditLog,
    ReadOnlyCapabilityBroker,
)


INVENTORY_CONFIG_VERSION = 1
MAX_CONFIG_BYTES = 65_536
MAX_ROOTS = 16
ROOT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


@dataclass(frozen=True)
class InventoryLimits:
    max_results: int = 200
    max_depth: int = 8
    max_items_examined: int = 10_000
    max_directories_examined: int = 1_000
    max_entries_per_directory: int = 2_000


@dataclass(frozen=True)
class InventoryRoot:
    root_id: str
    path: Path
    added_at: str


class InventoryRootStore:
    """Human-managed allowlist for metadata-only inventory roots."""

    def __init__(
        self,
        path: Path,
        *,
        home: Path | None = None,
        environment: Mapping[str, str] | None = None,
    ):
        self.path = path
        self.home = (home or Path.home()).expanduser().resolve()
        self.environment = dict(os.environ if environment is None else environment)

    @staticmethod
    def validate_root_id(root_id: str) -> str:
        if not isinstance(root_id, str) or not ROOT_ID_PATTERN.fullmatch(root_id):
            raise BrokerPolicyViolation(
                "Root ID must start with a lowercase letter and contain only "
                "lowercase letters, numbers, hyphens, or underscores"
            )
        return root_id

    @staticmethod
    def validate_added_at(value: str) -> str:
        if not isinstance(value, str) or len(value) > 64:
            raise BrokerPolicyViolation("Inventory root timestamp is invalid")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise BrokerPolicyViolation("Inventory root timestamp is invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise BrokerPolicyViolation("Inventory root timestamp must include a timezone")
        return value

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

    def _protected_subtrees(self) -> list[Path]:
        values = [
            self.home / "AppData",
            self.home / ".ssh",
            self.home / ".gnupg",
        ]
        for name in (
            "LOCALAPPDATA",
            "APPDATA",
            "PROGRAMDATA",
            "PROGRAMFILES",
            "PROGRAMFILES(X86)",
            "WINDIR",
        ):
            value = self.environment.get(name)
            if value:
                values.append(Path(value).expanduser().resolve())
        unique: list[Path] = []
        for value in values:
            if not any(self._same_path(value, existing) for existing in unique):
                unique.append(value)
        return unique

    def validate_root_path(self, value: Path) -> Path:
        expanded = value.expanduser()
        if ReadOnlyCapabilityBroker._is_reparse_point(expanded):
            raise BrokerPolicyViolation("Links, junctions, and reparse points cannot be roots")
        resolved = expanded.resolve(strict=True)
        if not resolved.is_dir():
            raise BrokerPolicyViolation("Inventory root must be an existing directory")
        if not resolved.is_absolute() or self._same_path(resolved, Path(resolved.anchor)):
            raise BrokerPolicyViolation("Drive and filesystem roots cannot be inventory roots")
        if self._same_path(resolved, self.home) or self._is_within(self.home, resolved):
            raise BrokerPolicyViolation(
                "The user profile or one of its parent directories is too broad to inventory"
            )
        if ReadOnlyCapabilityBroker._is_reparse_point(resolved):
            raise BrokerPolicyViolation("Links, junctions, and reparse points cannot be roots")
        if ReadOnlyCapabilityBroker._is_hidden_or_system(resolved):
            raise BrokerPolicyViolation("Hidden or system directories cannot be inventory roots")
        if resolved.name.casefold() in ReadOnlyCapabilityBroker.BLOCKED_NAMES:
            raise BrokerPolicyViolation("Protected directories cannot be inventory roots")
        for protected in self._protected_subtrees():
            if self._is_within(resolved, protected):
                raise BrokerPolicyViolation(
                    f"Protected system or credential area cannot be inventoried: {protected.name}"
                )
        return resolved

    def load(self) -> list[InventoryRoot]:
        if not self.path.exists():
            return []
        if ReadOnlyCapabilityBroker._is_reparse_point(self.path):
            raise BrokerPolicyViolation("Inventory configuration cannot be a link or reparse point")
        if self.path.stat().st_size > MAX_CONFIG_BYTES:
            raise BrokerPolicyViolation("Inventory configuration is unexpectedly large")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BrokerPolicyViolation("Inventory configuration is invalid") from exc
        if not isinstance(payload, dict) or set(payload) != {"version", "roots"}:
            raise BrokerPolicyViolation("Inventory configuration has an unexpected structure")
        if payload["version"] != INVENTORY_CONFIG_VERSION or not isinstance(payload["roots"], list):
            raise BrokerPolicyViolation("Inventory configuration version is unsupported")
        if len(payload["roots"]) > MAX_ROOTS:
            raise BrokerPolicyViolation(f"No more than {MAX_ROOTS} inventory roots are allowed")

        records: list[InventoryRoot] = []
        for item in payload["roots"]:
            if not isinstance(item, dict) or set(item) != {"id", "path", "added_at"}:
                raise BrokerPolicyViolation("Inventory root record has an unexpected structure")
            root_id = self.validate_root_id(item["id"])
            if not isinstance(item["path"], str):
                raise BrokerPolicyViolation("Inventory root record contains invalid values")
            added_at = self.validate_added_at(item["added_at"])
            if any(existing.root_id == root_id for existing in records):
                raise BrokerPolicyViolation(f"Duplicate inventory root ID: {root_id}")
            path = self.validate_root_path(Path(item["path"]))
            if any(
                self._is_within(path, existing.path) or self._is_within(existing.path, path)
                for existing in records
            ):
                raise BrokerPolicyViolation("Overlapping inventory roots are not allowed")
            records.append(InventoryRoot(root_id, path, added_at))
        return sorted(records, key=lambda record: record.root_id)

    def _save(self, records: list[InventoryRoot]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": INVENTORY_CONFIG_VERSION,
            "roots": [
                {"id": item.root_id, "path": str(item.path), "added_at": item.added_at}
                for item in sorted(records, key=lambda record: record.root_id)
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

    def add(self, root_id: str, path: Path) -> InventoryRoot:
        validated_id = self.validate_root_id(root_id)
        validated_path = self.validate_root_path(path)
        records = self.load()
        if any(item.root_id == validated_id for item in records):
            raise BrokerPolicyViolation(f"Inventory root ID already exists: {validated_id}")
        for item in records:
            if self._is_within(validated_path, item.path) or self._is_within(
                item.path, validated_path
            ):
                raise BrokerPolicyViolation(
                    f"Inventory root overlaps existing root: {item.root_id}"
                )
        if len(records) >= MAX_ROOTS:
            raise BrokerPolicyViolation(f"No more than {MAX_ROOTS} inventory roots are allowed")
        record = InventoryRoot(
            validated_id,
            validated_path,
            datetime.now(timezone.utc).isoformat(),
        )
        self._save([*records, record])
        return record

    def remove(self, root_id: str) -> InventoryRoot:
        validated_id = self.validate_root_id(root_id)
        records = self.load()
        selected = next((item for item in records if item.root_id == validated_id), None)
        if selected is None:
            raise BrokerPolicyViolation(f"Unknown inventory root: {validated_id}")
        self._save([item for item in records if item.root_id != validated_id])
        return selected


class MetadataInventoryBroker:
    """Bounded metadata-only view over explicitly allowlisted directories."""

    DESIGN_EXTENSIONS = {
        ".afdesign",
        ".afphoto",
        ".ai",
        ".ait",
        ".cdr",
        ".clip",
        ".fig",
        ".idml",
        ".indd",
        ".kra",
        ".psb",
        ".psd",
        ".sai2",
        ".sketch",
        ".xd",
        ".xcf",
    }
    VECTOR_EXTENSIONS = {".eps", ".svg"}
    IMAGE_EXTENSIONS = {
        ".avif",
        ".bmp",
        ".gif",
        ".heic",
        ".jpeg",
        ".jpg",
        ".png",
        ".tif",
        ".tiff",
        ".webp",
    }
    RAW_EXTENSIONS = {
        ".arw",
        ".cr2",
        ".cr3",
        ".dng",
        ".nef",
        ".orf",
        ".raw",
        ".rw2",
    }
    FONT_EXTENSIONS = {".otf", ".ttf", ".woff", ".woff2"}
    THREE_D_EXTENSIONS = {".3ds", ".blend", ".fbx", ".glb", ".gltf", ".obj"}
    VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
    DOCUMENT_ASSET_EXTENSIONS = {".pdf"}

    def __init__(
        self,
        roots: list[InventoryRoot],
        audit_path: Path | None = None,
        limits: InventoryLimits | None = None,
    ):
        self.roots = {record.root_id: record for record in roots}
        self.views = {
            root_id: ReadOnlyCapabilityBroker(record.path, None)
            for root_id, record in self.roots.items()
        }
        self.audit = MetadataAuditLog(audit_path)
        self.limits = limits or InventoryLimits()

    def _view(self, root_id: str) -> ReadOnlyCapabilityBroker:
        if not isinstance(root_id, str) or root_id not in self.views:
            raise BrokerPolicyViolation(f"Unknown inventory root: {root_id}")
        root = self.roots[root_id].path
        if not root.exists() or not root.is_dir():
            raise BrokerPolicyViolation("Approved inventory root is no longer available")
        if ReadOnlyCapabilityBroker._is_reparse_point(root):
            raise BrokerPolicyViolation("Approved inventory root became a link or reparse point")
        return self.views[root_id]

    def status(self) -> dict[str, object]:
        result = {
            "mode": "metadata-only",
            "content_reads": False,
            "write_operations": False,
            "classification_basis": "file extension only",
            "roots": [
                {"root_id": item.root_id, "path": str(item.path)}
                for item in sorted(self.roots.values(), key=lambda record: record.root_id)
            ],
            "limits": {
                "max_roots": MAX_ROOTS,
                "max_results": self.limits.max_results,
                "max_depth": self.limits.max_depth,
                "max_items_examined": self.limits.max_items_examined,
                "max_directories_examined": self.limits.max_directories_examined,
                "max_entries_per_directory": self.limits.max_entries_per_directory,
            },
        }
        self.audit.record("inventory_status", "[inventory]", True, roots=len(self.roots))
        return result

    def list_directory(
        self, root_id: str, relative_directory: str = ".", max_results: int = 100
    ) -> dict[str, object]:
        limit = self._validate_result_limit(max_results)
        view = self._view(root_id)
        directory = view.resolve(relative_directory, require_dir=True)
        self._recheck_directory(view, directory)
        entries: list[dict[str, object]] = []
        skipped = 0
        truncated = False
        try:
            iterator = os.scandir(directory)
            with iterator:
                children = []
                for index, entry in enumerate(iterator):
                    if index >= self.limits.max_entries_per_directory:
                        truncated = True
                        break
                    children.append(Path(entry.path))
            children.sort(key=lambda item: item.name.casefold())
        except OSError as exc:
            raise BrokerPolicyViolation("Directory metadata could not be listed") from exc
        for index, item in enumerate(children):
            try:
                view._validate_name(item)
                if view._is_reparse_point(item):
                    skipped += 1
                    continue
                info = item.stat(follow_symlinks=False)
                kind = "directory" if item.is_dir() else "file" if item.is_file() else "other"
                entries.append(self._metadata(view.root, item, kind, info))
            except (BrokerPolicyViolation, OSError):
                skipped += 1
                continue
            if len(entries) >= limit:
                truncated = truncated or len(children) > index + 1
                break
        result = {
            "root_id": root_id,
            "relative_directory": relative_directory or ".",
            "entries": entries,
            "returned": len(entries),
            "skipped_protected": skipped,
            "truncated": truncated,
            "content_read": False,
        }
        self._record("inventory_list_directory", root_id, result)
        return result

    def summarize(
        self, root_id: str, relative_directory: str = ".", max_depth: int = 3
    ) -> dict[str, object]:
        scan = self._scan(root_id, relative_directory, max_depth, candidate_limit=None)
        extension_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        total_bytes = 0
        for item in scan["files"]:
            extension = str(item["extension"] or "[no extension]")
            extension_counts[extension] = extension_counts.get(extension, 0) + 1
            total_bytes += int(item["size_bytes"])
            classification = self._classify(str(item["extension"]))
            if classification is not None:
                category = classification[0]
                category_counts[category] = category_counts.get(category, 0) + 1
        result = {
            "root_id": root_id,
            "relative_directory": relative_directory or ".",
            "max_depth": max_depth,
            "files_examined": scan["files_examined"],
            "directories_examined": scan["directories_examined"],
            "total_file_bytes": total_bytes,
            "extension_counts": dict(
                sorted(extension_counts.items(), key=lambda item: (-item[1], item[0]))[:100]
            ),
            "graphic_category_counts": dict(sorted(category_counts.items())),
            "skipped_protected_or_unavailable": scan["skipped"],
            "truncated": scan["truncated"],
            "content_read": False,
        }
        self._record("inventory_summarize", root_id, result)
        return result

    def graphic_candidates(
        self,
        root_id: str,
        relative_directory: str = ".",
        max_depth: int = 3,
        max_results: int = 100,
    ) -> dict[str, object]:
        limit = self._validate_result_limit(max_results)
        scan = self._scan(root_id, relative_directory, max_depth, candidate_limit=limit)
        candidates: list[dict[str, object]] = []
        for item in scan["files"]:
            classification = self._classify(str(item["extension"]))
            if classification is None:
                continue
            category, confidence = classification
            candidates.append(
                {
                    **item,
                    "category": category,
                    "confidence": confidence,
                    "reason": f"Extension {item['extension']} is in the {category} allowlist.",
                }
            )
        candidates.sort(key=lambda item: str(item["relative_path"]).casefold())
        if len(candidates) > limit:
            candidates = candidates[:limit]
            scan["truncated"] = True
        result = {
            "root_id": root_id,
            "relative_directory": relative_directory or ".",
            "max_depth": max_depth,
            "classification_basis": "extension only; usage inside design projects is not inspected",
            "candidates": candidates,
            "returned": len(candidates),
            "files_examined": scan["files_examined"],
            "directories_examined": scan["directories_examined"],
            "skipped_protected_or_unavailable": scan["skipped"],
            "truncated": scan["truncated"],
            "content_read": False,
        }
        self._record("inventory_graphic_candidates", root_id, result)
        return result

    def _scan(
        self,
        root_id: str,
        relative_directory: str,
        max_depth: int,
        candidate_limit: int | None,
    ) -> dict[str, object]:
        depth_limit = self._validate_depth(max_depth)
        view = self._view(root_id)
        start = view.resolve(relative_directory, require_dir=True)
        stack: list[tuple[Path, int]] = [(start, 0)]
        files: list[dict[str, object]] = []
        files_examined = 0
        directories_examined = 0
        items_examined = 0
        skipped = 0
        truncated = False
        candidates_found = 0

        while stack:
            if directories_examined >= self.limits.max_directories_examined:
                truncated = True
                break
            directory, depth = stack.pop()
            directories_examined += 1
            try:
                self._recheck_directory(view, directory)
                iterator = os.scandir(directory)
                with iterator:
                    children = []
                    for index, entry in enumerate(iterator):
                        if index >= self.limits.max_entries_per_directory:
                            truncated = True
                            break
                        children.append(entry)
            except OSError:
                skipped += 1
                continue
            children.sort(key=lambda entry: entry.name.casefold(), reverse=True)
            for child_index, entry in enumerate(children):
                if items_examined >= self.limits.max_items_examined:
                    truncated = True
                    stack.clear()
                    break
                items_examined += 1
                path = Path(entry.path)
                try:
                    view._validate_name(path)
                    if entry.is_symlink() or view._is_reparse_point(path):
                        skipped += 1
                        continue
                    info = entry.stat(follow_symlinks=False)
                    if entry.is_dir(follow_symlinks=False):
                        if depth < depth_limit:
                            stack.append((path, depth + 1))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        skipped += 1
                        continue
                    files_examined += 1
                    metadata = self._metadata(view.root, path, "file", info)
                    files.append(metadata)
                    if candidate_limit is not None and self._classify(str(metadata["extension"])):
                        candidates_found += 1
                        if candidates_found >= candidate_limit:
                            truncated = (
                                truncated
                                or bool(stack)
                                or child_index < len(children) - 1
                            )
                            stack.clear()
                            break
                except (BrokerPolicyViolation, OSError):
                    skipped += 1
                    continue
        return {
            "files": files,
            "files_examined": files_examined,
            "directories_examined": directories_examined,
            "skipped": skipped,
            "truncated": truncated,
        }

    @staticmethod
    def _recheck_directory(view: ReadOnlyCapabilityBroker, directory: Path) -> None:
        """Best-effort recheck immediately before a directory handle is opened."""
        if ReadOnlyCapabilityBroker._is_reparse_point(directory):
            raise BrokerPolicyViolation("Links and reparse points are not accessible")
        resolved = directory.resolve(strict=True)
        try:
            resolved.relative_to(view.root)
        except ValueError as exc:
            raise BrokerPolicyViolation("Directory escaped the approved inventory root") from exc
        if not resolved.is_dir():
            raise BrokerPolicyViolation("Requested inventory path is not a directory")

    @staticmethod
    def _metadata(root: Path, path: Path, kind: str, info: os.stat_result) -> dict[str, object]:
        return {
            "relative_path": path.relative_to(root).as_posix(),
            "type": kind,
            "extension": path.suffix.casefold() if kind == "file" else "",
            "size_bytes": info.st_size if kind == "file" else None,
            "modified_utc": datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat(),
        }

    def _validate_result_limit(self, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise BrokerPolicyViolation("max_results must be an integer")
        if value < 1 or value > self.limits.max_results:
            raise BrokerPolicyViolation(
                f"max_results must be from 1 to {self.limits.max_results}"
            )
        return value

    def _validate_depth(self, value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise BrokerPolicyViolation("max_depth must be an integer")
        if value < 0 or value > self.limits.max_depth:
            raise BrokerPolicyViolation(f"max_depth must be from 0 to {self.limits.max_depth}")
        return value

    def _classify(self, extension: str) -> tuple[str, str] | None:
        if extension in self.DESIGN_EXTENSIONS:
            return "design_source", "high"
        if extension in self.VECTOR_EXTENSIONS:
            return "vector_asset", "high"
        if extension in self.IMAGE_EXTENSIONS:
            return "image_asset", "high"
        if extension in self.RAW_EXTENSIONS:
            return "raw_photo", "high"
        if extension in self.FONT_EXTENSIONS:
            return "font_asset", "high"
        if extension in self.THREE_D_EXTENSIONS:
            return "3d_asset", "medium"
        if extension in self.VIDEO_EXTENSIONS:
            return "video_asset", "medium"
        if extension in self.DOCUMENT_ASSET_EXTENSIONS:
            return "document_asset", "medium"
        return None

    def _record(self, tool: str, root_id: str, result: dict[str, object]) -> None:
        self.audit.record(
            tool,
            "[inventory]",
            True,
            root_id=root_id,
            returned=result.get("returned"),
            files_examined=result.get("files_examined"),
            directories_examined=result.get("directories_examined"),
            truncated=result.get("truncated"),
        )
