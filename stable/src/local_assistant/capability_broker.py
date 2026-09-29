from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePath
import re
import stat
import threading
import uuid


class BrokerPolicyViolation(RuntimeError):
    """Raised when a broker request crosses the configured security boundary."""


@dataclass(frozen=True)
class BrokerLimits:
    max_list_entries: int = 200
    max_read_bytes: int = 65_536


class MetadataAuditLog:
    """Append-only JSONL audit log that never records file contents."""

    def __init__(self, path: Path | None):
        self.path = path
        self._lock = threading.Lock()
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, tool: str, relative_path: str, success: bool, **metadata: object) -> None:
        if self.path is None:
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": uuid.uuid4().hex,
            "tool": tool,
            "relative_path": relative_path,
            "success": success,
            "metadata": metadata,
        }
        line = json.dumps(record, ensure_ascii=True, separators=(",", ":"))
        with self._lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(line + "\n")


class ReadOnlyCapabilityBroker:
    """A narrow, default-deny filesystem view rooted at one user-approved folder."""

    SAFE_TEXT_EXTENSIONS = {
        ".csv",
        ".json",
        ".log",
        ".md",
        ".rst",
        ".txt",
        ".yaml",
        ".yml",
    }
    BLOCKED_NAMES = {
        ".env",
        ".git",
        ".ssh",
        "auth.json",
        "credentials.json",
        "id_dsa",
        "id_ed25519",
        "id_rsa",
        "login data",
        "ntuser.dat",
        "secrets.json",
    }
    WINDOWS_RESERVED_STEMS = {
        "aux",
        "clock$",
        "con",
        "nul",
        "prn",
        *(f"com{number}" for number in range(1, 10)),
        *(f"lpt{number}" for number in range(1, 10)),
    }
    DOS_SHORT_NAME = re.compile(r"^[^~]{1,6}~[1-9](?:\..*)?$", re.IGNORECASE)

    def __init__(
        self,
        root: Path,
        audit_path: Path | None = None,
        limits: BrokerLimits | None = None,
    ):
        resolved = root.expanduser().resolve(strict=True)
        if not resolved.is_dir():
            raise ValueError(f"Broker root is not a directory: {resolved}")
        self.root = resolved
        self.root_name = resolved.name
        self.limits = limits or BrokerLimits()
        self.audit = MetadataAuditLog(audit_path)

    @staticmethod
    def _is_reparse_point(path: Path) -> bool:
        if path.is_symlink():
            return True
        isjunction = getattr(os.path, "isjunction", None)
        if isjunction is not None and isjunction(path):
            return True
        try:
            return bool(path.stat(follow_symlinks=False).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
        except (AttributeError, OSError):
            return False

    @staticmethod
    def _is_hidden_or_system(path: Path) -> bool:
        if path.name.startswith("."):
            return True
        try:
            attributes = path.stat(follow_symlinks=False).st_file_attributes
            blocked = stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM
            return bool(attributes & blocked)
        except (AttributeError, OSError):
            return False

    def _validate_name(self, path: Path) -> None:
        if path.name.casefold() in self.BLOCKED_NAMES:
            raise BrokerPolicyViolation(f"Protected name is not accessible: {path.name}")
        if self._is_hidden_or_system(path):
            raise BrokerPolicyViolation(f"Hidden or system item is not accessible: {path.name}")

    @classmethod
    def _validate_portable_component(cls, component: str) -> None:
        """Reject names whose Windows canonical form can refer to another path."""
        if not component or component in {".", ".."}:
            raise BrokerPolicyViolation("Path traversal is not allowed")
        if component != component.rstrip(" ."):
            raise BrokerPolicyViolation("Trailing spaces or dots are not allowed in paths")
        if any(ord(character) < 32 for character in component):
            raise BrokerPolicyViolation("Control characters are not allowed in paths")
        stem = component.split(".", 1)[0].casefold()
        if stem in cls.WINDOWS_RESERVED_STEMS:
            raise BrokerPolicyViolation(f"Windows device name is not accessible: {component}")
        if cls.DOS_SHORT_NAME.fullmatch(component):
            raise BrokerPolicyViolation(f"DOS short-name aliases are not accessible: {component}")

    def resolve(self, relative_path: str, *, require_file: bool = False, require_dir: bool = False) -> Path:
        if not isinstance(relative_path, str):
            raise BrokerPolicyViolation("Path must be text")
        value = relative_path
        if value != value.strip():
            raise BrokerPolicyViolation("Leading or trailing whitespace is not allowed in paths")
        if value in {"", "."}:
            candidate_parts: tuple[str, ...] = ()
        else:
            portable = PurePath(value.replace("\\", "/"))
            if portable.is_absolute() or ":" in value:
                raise BrokerPolicyViolation("Absolute or drive-qualified paths are not allowed")
            if any(part in {"", ".", ".."} for part in portable.parts):
                raise BrokerPolicyViolation("Path traversal is not allowed")
            candidate_parts = portable.parts

        for part in candidate_parts:
            self._validate_portable_component(part)

        current = self.root
        for part in candidate_parts:
            current = current / part
            if not current.exists():
                raise BrokerPolicyViolation(f"Path does not exist: {relative_path}")
            self._validate_name(current)
            if self._is_reparse_point(current):
                raise BrokerPolicyViolation(f"Links and reparse points are not accessible: {part}")

        resolved = current.resolve(strict=True)
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise BrokerPolicyViolation("Resolved path escaped the approved root") from exc
        if require_file and not resolved.is_file():
            raise BrokerPolicyViolation("Requested path is not a file")
        if require_dir and not resolved.is_dir():
            raise BrokerPolicyViolation("Requested path is not a directory")
        return resolved

    def resolve_new_target(self, relative_path: str, *, planned_parents: frozenset[Path] = frozenset()) -> Path:
        """Resolve a not-yet-existing child while validating every existing parent."""
        if not isinstance(relative_path, str):
            raise BrokerPolicyViolation("Path must be text")
        value = relative_path
        if value != value.strip():
            raise BrokerPolicyViolation("Leading or trailing whitespace is not allowed in paths")
        portable = PurePath(value.replace("\\", "/"))
        if not value or value == "." or portable.is_absolute() or ":" in value:
            raise BrokerPolicyViolation("A non-root relative path is required")
        if any(part in {"", ".", ".."} for part in portable.parts):
            raise BrokerPolicyViolation("Path traversal is not allowed")
        for part in portable.parts:
            self._validate_portable_component(part)
        parent_text = "/".join(portable.parts[:-1]) or "."
        proposed_parent = self.root.joinpath(*portable.parts[:-1])
        if proposed_parent in planned_parents:
            # Only earlier mkdir actions in the same reviewed plan may supply missing parents.
            current = proposed_parent
            while current in planned_parents:
                if current.exists() or current.is_symlink():
                    raise BrokerPolicyViolation("A planned directory already exists")
                current = current.parent
            self.resolve(current.relative_to(self.root).as_posix() or ".", require_dir=True)
            parent = proposed_parent
        else:
            parent = self.resolve(parent_text, require_dir=True)
        target = parent / portable.parts[-1]
        self._validate_name(target)
        if target.exists() or target.is_symlink():
            raise BrokerPolicyViolation(f"Refusing to overwrite existing path: {relative_path}")
        try:
            target.relative_to(self.root)
        except ValueError as exc:
            raise BrokerPolicyViolation("Target escaped the approved root") from exc
        return target

    def status(self) -> dict[str, object]:
        result = {
            "mode": "read-only",
            "root": str(self.root),
            "root_name": self.root_name,
            "write_operations": False,
            "max_list_entries": self.limits.max_list_entries,
            "max_read_bytes": self.limits.max_read_bytes,
        }
        self.audit.record("sandbox_status", ".", True)
        return result

    def list_directory(
        self, relative_path: str = ".", max_entries: int | None = None
    ) -> dict[str, object]:
        requested_limit = min(100, self.limits.max_list_entries) if max_entries is None else int(max_entries)
        if requested_limit < 1 or requested_limit > self.limits.max_list_entries:
            raise BrokerPolicyViolation(
                f"max_entries must be from 1 to {self.limits.max_list_entries}"
            )
        directory = self.resolve(relative_path, require_dir=True)
        entries: list[dict[str, object]] = []
        skipped = 0
        for item in sorted(directory.iterdir(), key=lambda value: value.name.casefold()):
            try:
                self._validate_name(item)
                if self._is_reparse_point(item):
                    skipped += 1
                    continue
                kind = "directory" if item.is_dir() else "file" if item.is_file() else "other"
                info = item.stat(follow_symlinks=False)
                entries.append(
                    {
                        "name": item.name,
                        "type": kind,
                        "size": info.st_size if kind == "file" else None,
                        "modified_utc": datetime.fromtimestamp(
                            info.st_mtime, timezone.utc
                        ).isoformat(),
                    }
                )
            except (BrokerPolicyViolation, OSError):
                skipped += 1
                continue
            if len(entries) >= requested_limit:
                break
        result = {
            "path": relative_path or ".",
            "entries": entries,
            "returned": len(entries),
            "skipped_protected": skipped,
            "limit": requested_limit,
        }
        self.audit.record(
            "sandbox_list", relative_path or ".", True, returned=len(entries), skipped=skipped
        )
        return result

    def read_text(self, relative_path: str, max_bytes: int | None = None) -> dict[str, object]:
        requested_limit = min(32_768, self.limits.max_read_bytes) if max_bytes is None else int(max_bytes)
        if requested_limit < 1 or requested_limit > self.limits.max_read_bytes:
            raise BrokerPolicyViolation(
                f"max_bytes must be from 1 to {self.limits.max_read_bytes}"
            )
        path = self.resolve(relative_path, require_file=True)
        if path.suffix.casefold() not in self.SAFE_TEXT_EXTENSIONS:
            raise BrokerPolicyViolation(
                "Only approved plain-text file types may be read in this milestone"
            )
        size = path.stat().st_size
        if size > requested_limit:
            raise BrokerPolicyViolation(
                f"File is {size} bytes; requested read limit is {requested_limit} bytes"
            )
        payload = path.read_bytes()
        if b"\x00" in payload:
            raise BrokerPolicyViolation("Binary content is not allowed")
        try:
            content = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise BrokerPolicyViolation("File is not valid UTF-8 text") from exc
        result = {
            "path": relative_path,
            "bytes": len(payload),
            "content": content,
        }
        self.audit.record("sandbox_read_text", relative_path, True, bytes=len(payload))
        return result
