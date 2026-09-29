from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Mapping, Protocol
import uuid

from .capability_broker import (
    BrokerPolicyViolation,
    MetadataAuditLog,
    ReadOnlyCapabilityBroker,
)


WINDOWS_APP_CONFIG_VERSION = 2
MAX_WINDOWS_APPS = 32
MAX_WINDOWS_CONFIG_BYTES = 65_536
APP_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")
APP_USER_MODEL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._!+\-]{0,127}$")
WINDOW_ID_PATTERN = re.compile(r"^[1-9][0-9]{0,19}$")


@dataclass(frozen=True)
class WindowsApp:
    app_id: str
    display_name: str
    executable: Path
    added_at: str
    app_user_model_id: str | None = None
    allow_text_entry: bool = False


class WindowsAppStore:
    """Human-managed allowlist of exact executables Cypher may start."""

    def __init__(self, path: Path, *, environment: Mapping[str, str] | None = None):
        self.path = path
        self.environment = dict(os.environ if environment is None else environment)

    @staticmethod
    def validate_app_id(value: str) -> str:
        if not isinstance(value, str) or not APP_ID_PATTERN.fullmatch(value):
            raise BrokerPolicyViolation(
                "App ID must start with a lowercase letter and contain only lowercase "
                "letters, numbers, hyphens, or underscores"
            )
        return value

    @staticmethod
    def validate_display_name(value: str) -> str:
        if not isinstance(value, str):
            raise BrokerPolicyViolation("Display name must be text")
        normalized = value.strip()
        if not normalized or len(normalized) > 64 or any(ord(char) < 32 for char in normalized):
            raise BrokerPolicyViolation("Display name must contain 1 to 64 printable characters")
        return normalized

    @staticmethod
    def validate_added_at(value: str) -> str:
        if not isinstance(value, str) or len(value) > 64:
            raise BrokerPolicyViolation("Windows app timestamp is invalid")
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError as exc:
            raise BrokerPolicyViolation("Windows app timestamp is invalid") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise BrokerPolicyViolation("Windows app timestamp must include a timezone")
        return value

    @staticmethod
    def validate_app_user_model_id(value: str | None) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise BrokerPolicyViolation("Windows AppUserModelID must be text or null")
        normalized = value.strip()
        if not APP_USER_MODEL_ID_PATTERN.fullmatch(normalized):
            raise BrokerPolicyViolation(
                "Windows AppUserModelID must contain 1 to 128 safe identifier characters"
            )
        return normalized

    @staticmethod
    def validate_executable(value: Path) -> Path:
        expanded = value.expanduser()
        if not expanded.is_absolute():
            raise BrokerPolicyViolation("Windows app executable must be an absolute path")
        if ReadOnlyCapabilityBroker._is_reparse_point(expanded):
            raise BrokerPolicyViolation("Windows app executable cannot be a link or reparse point")
        try:
            resolved = expanded.resolve(strict=True)
        except OSError as exc:
            raise BrokerPolicyViolation("Windows app executable does not exist") from exc
        if not resolved.is_file() or resolved.suffix.casefold() != ".exe":
            raise BrokerPolicyViolation("Windows app target must be an existing .exe file")
        if ReadOnlyCapabilityBroker._is_reparse_point(resolved):
            raise BrokerPolicyViolation("Windows app executable cannot be a link or reparse point")
        return resolved

    def load(self) -> list[WindowsApp]:
        if not self.path.exists():
            return []
        if ReadOnlyCapabilityBroker._is_reparse_point(self.path):
            raise BrokerPolicyViolation("Windows app configuration cannot be a link")
        if self.path.stat().st_size > MAX_WINDOWS_CONFIG_BYTES:
            raise BrokerPolicyViolation("Windows app configuration is unexpectedly large")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BrokerPolicyViolation("Windows app configuration is invalid") from exc
        if not isinstance(payload, dict) or set(payload) != {"version", "apps"}:
            raise BrokerPolicyViolation("Windows app configuration has an unexpected structure")
        if payload["version"] not in {1, WINDOWS_APP_CONFIG_VERSION} or not isinstance(payload["apps"], list):
            raise BrokerPolicyViolation("Windows app configuration version is unsupported")
        if len(payload["apps"]) > MAX_WINDOWS_APPS:
            raise BrokerPolicyViolation(
                f"No more than {MAX_WINDOWS_APPS} Windows apps are allowed"
            )

        records: list[WindowsApp] = []
        for item in payload["apps"]:
            expected = {"id", "display_name", "executable", "added_at"}
            if payload["version"] == WINDOWS_APP_CONFIG_VERSION:
                expected |= {"app_user_model_id", "allow_text_entry"}
            if not isinstance(item, dict) or set(item) != expected:
                raise BrokerPolicyViolation("Windows app record has an unexpected structure")
            app_id = self.validate_app_id(item["id"])
            display_name = self.validate_display_name(item["display_name"])
            if not isinstance(item["executable"], str):
                raise BrokerPolicyViolation("Windows app executable path is invalid")
            executable = self.validate_executable(Path(item["executable"]))
            added_at = self.validate_added_at(item["added_at"])
            app_user_model_id = self.validate_app_user_model_id(
                item.get("app_user_model_id")
            )
            allow_text_entry = item.get("allow_text_entry", False)
            if not isinstance(allow_text_entry, bool):
                raise BrokerPolicyViolation("Windows app text-entry capability must be boolean")
            if any(record.app_id == app_id for record in records):
                raise BrokerPolicyViolation(f"Duplicate Windows app ID: {app_id}")
            if any(os.path.normcase(str(record.executable)) == os.path.normcase(str(executable)) for record in records):
                raise BrokerPolicyViolation("The same Windows executable is registered more than once")
            if app_user_model_id and any(
                record.app_user_model_id
                and record.app_user_model_id.casefold() == app_user_model_id.casefold()
                for record in records
            ):
                raise BrokerPolicyViolation("The same Windows AppUserModelID is registered more than once")
            records.append(
                WindowsApp(
                    app_id,
                    display_name,
                    executable,
                    added_at,
                    app_user_model_id,
                    allow_text_entry,
                )
            )
        return sorted(records, key=lambda record: record.app_id)

    def _save(self, records: list[WindowsApp]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": WINDOWS_APP_CONFIG_VERSION,
            "apps": [
                {
                    "id": record.app_id,
                    "display_name": record.display_name,
                    "executable": str(record.executable),
                    "added_at": record.added_at,
                    "app_user_model_id": record.app_user_model_id,
                    "allow_text_entry": record.allow_text_entry,
                }
                for record in sorted(records, key=lambda record: record.app_id)
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
        self,
        app_id: str,
        display_name: str,
        executable: Path,
        *,
        app_user_model_id: str | None = None,
        allow_text_entry: bool = False,
    ) -> WindowsApp:
        validated_id = self.validate_app_id(app_id)
        validated_name = self.validate_display_name(display_name)
        validated_executable = self.validate_executable(executable)
        validated_app_user_model_id = self.validate_app_user_model_id(app_user_model_id)
        if not isinstance(allow_text_entry, bool):
            raise BrokerPolicyViolation("Windows app text-entry capability must be boolean")
        records = self.load()
        if any(record.app_id == validated_id for record in records):
            raise BrokerPolicyViolation(f"Windows app ID already exists: {validated_id}")
        if any(
            os.path.normcase(str(record.executable))
            == os.path.normcase(str(validated_executable))
            for record in records
        ):
            raise BrokerPolicyViolation("This Windows executable is already registered")
        if validated_app_user_model_id and any(
            record.app_user_model_id
            and record.app_user_model_id.casefold() == validated_app_user_model_id.casefold()
            for record in records
        ):
            raise BrokerPolicyViolation("This Windows AppUserModelID is already registered")
        if len(records) >= MAX_WINDOWS_APPS:
            raise BrokerPolicyViolation(
                f"No more than {MAX_WINDOWS_APPS} Windows apps are allowed"
            )
        record = WindowsApp(
            validated_id,
            validated_name,
            validated_executable,
            datetime.now(timezone.utc).isoformat(),
            validated_app_user_model_id,
            allow_text_entry,
        )
        self._save([*records, record])
        return record

    def remove(self, app_id: str) -> WindowsApp:
        validated_id = self.validate_app_id(app_id)
        records = self.load()
        selected = next((record for record in records if record.app_id == validated_id), None)
        if selected is None:
            raise BrokerPolicyViolation(f"Unknown Windows app: {validated_id}")
        self._save([record for record in records if record.app_id != validated_id])
        return selected

    def set_text_entry(self, app_id: str, enabled: bool) -> WindowsApp:
        validated_id = self.validate_app_id(app_id)
        if not isinstance(enabled, bool):
            raise BrokerPolicyViolation("Windows app text-entry capability must be boolean")
        records = self.load()
        selected = next((record for record in records if record.app_id == validated_id), None)
        if selected is None:
            raise BrokerPolicyViolation(f"Unknown Windows app: {validated_id}")
        replacement = WindowsApp(
            selected.app_id,
            selected.display_name,
            selected.executable,
            selected.added_at,
            selected.app_user_model_id,
            enabled,
        )
        self._save([replacement if record.app_id == validated_id else record for record in records])
        return replacement

    def set_app_user_model_id(self, app_id: str, value: str | None) -> WindowsApp:
        validated_id = self.validate_app_id(app_id)
        validated_value = self.validate_app_user_model_id(value)
        records = self.load()
        selected = next((record for record in records if record.app_id == validated_id), None)
        if selected is None:
            raise BrokerPolicyViolation(f"Unknown Windows app: {validated_id}")
        if validated_value and any(
            record.app_id != validated_id
            and record.app_user_model_id
            and record.app_user_model_id.casefold() == validated_value.casefold()
            for record in records
        ):
            raise BrokerPolicyViolation("This Windows AppUserModelID is already registered")
        replacement = WindowsApp(
            selected.app_id,
            selected.display_name,
            selected.executable,
            selected.added_at,
            validated_value,
            selected.allow_text_entry,
        )
        self._save([replacement if record.app_id == validated_id else record for record in records])
        return replacement

    @staticmethod
    def discover_start_app_ids() -> dict[str, str]:
        if os.name != "nt":
            return {}
        command = (
            "Get-StartApps | Select-Object Name,AppID | "
            "ConvertTo-Json -Compress"
        )
        try:
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    command,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
                shell=False,
            )
            if len(completed.stdout) > MAX_WINDOWS_CONFIG_BYTES:
                return {}
            payload = json.loads(completed.stdout or "[]")
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return {}
        if isinstance(payload, dict):
            payload = [payload]
        if not isinstance(payload, list):
            return {}
        discovered: dict[str, str] = {}
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("Name")
            app_id = item.get("AppID")
            if not isinstance(name, str) or not isinstance(app_id, str):
                continue
            try:
                discovered[name] = WindowsAppStore.validate_app_user_model_id(app_id) or ""
            except BrokerPolicyViolation:
                continue
        return discovered

    def seed_builtin_apps(
        self, *, start_apps: Mapping[str, str] | None = None
    ) -> dict[str, object]:
        windows_root = self.environment.get("WINDIR")
        if not windows_root:
            raise BrokerPolicyViolation("WINDIR is unavailable; built-in apps were not seeded")
        root = Path(windows_root)
        discovered = dict(self.discover_start_app_ids() if start_apps is None else start_apps)

        def packaged_id(prefix: str) -> str | None:
            matches = sorted(
                value
                for value in discovered.values()
                if isinstance(value, str) and value.casefold().startswith(prefix.casefold())
            )
            if len(matches) != 1:
                return None
            return self.validate_app_user_model_id(matches[0])

        candidates = (
            (
                "notepad",
                "Notepad",
                root / "System32" / "notepad.exe",
                packaged_id("Microsoft.WindowsNotepad_"),
                False,
            ),
            (
                "calculator",
                "Calculator",
                root / "System32" / "calc.exe",
                packaged_id("Microsoft.WindowsCalculator_"),
                False,
            ),
            ("paint", "Paint", root / "System32" / "mspaint.exe", None, False),
            ("file-explorer", "File Explorer", root / "explorer.exe", None, False),
        )
        existing = self.load()
        existing_ids = {record.app_id for record in existing}
        existing_paths = {os.path.normcase(str(record.executable)) for record in existing}
        added: list[str] = []
        upgraded: list[str] = []
        unavailable: list[str] = []
        for app_id, display_name, executable, app_user_model_id, allow_text_entry in candidates:
            if app_user_model_id and any(
                record.app_id != app_id
                and record.app_user_model_id
                and record.app_user_model_id.casefold() == app_user_model_id.casefold()
                for record in existing
            ):
                raise BrokerPolicyViolation(
                    "A discovered Windows AppUserModelID is already assigned to another app"
                )
            if app_id in existing_ids:
                current = next(record for record in existing if record.app_id == app_id)
                replacement = WindowsApp(
                    current.app_id,
                    current.display_name,
                    current.executable,
                    current.added_at,
                    app_user_model_id or current.app_user_model_id,
                    current.allow_text_entry or allow_text_entry,
                )
                if replacement != current:
                    existing = [replacement if record.app_id == app_id else record for record in existing]
                    upgraded.append(app_id)
                continue
            try:
                validated = self.validate_executable(executable)
            except BrokerPolicyViolation:
                unavailable.append(app_id)
                continue
            if os.path.normcase(str(validated)) in existing_paths:
                continue
            record = WindowsApp(
                app_id,
                display_name,
                validated,
                datetime.now(timezone.utc).isoformat(),
                app_user_model_id,
                allow_text_entry,
            )
            existing.append(record)
            existing_ids.add(app_id)
            existing_paths.add(os.path.normcase(str(validated)))
            added.append(app_id)
        # Always persist the validated result so a human-run seed operation also
        # migrates an otherwise unchanged version-1 registry to version 2.
        self._save(existing)
        return {
            "added": added,
            "upgraded": upgraded,
            "unavailable": unavailable,
            "registered": len(existing),
        }


class WindowsBackend(Protocol):
    def list_windows(self, max_results: int) -> list[dict[str, object]]: ...

    def foreground_window(self) -> dict[str, object] | None: ...

    def launch(self, executable: Path) -> int: ...

    def focus(self, window_id: str) -> dict[str, object]: ...


class NativeWindowsBackend:
    """Small ctypes adapter for top-level window observation and activation."""

    def __init__(self):
        if sys.platform != "win32":
            raise BrokerPolicyViolation("Windows desktop control is available only on Windows")
        import ctypes
        from ctypes import wintypes

        self.ctypes = ctypes
        self.wintypes = wintypes
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        self.user32.EnumWindows.argtypes = [self.callback_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsIconic.argtypes = [wintypes.HWND]
        self.user32.IsIconic.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.user32.GetWindowThreadProcessId.restype = wintypes.DWORD
        self.user32.GetForegroundWindow.argtypes = []
        self.user32.GetForegroundWindow.restype = wintypes.HWND
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindowAsync.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL

    def _hwnd(self, window_id: str):
        if not isinstance(window_id, str) or not WINDOW_ID_PATTERN.fullmatch(window_id):
            raise BrokerPolicyViolation("window_id must be a positive decimal window handle")
        return self.wintypes.HWND(int(window_id))

    def _window_id(self, hwnd) -> str:
        value = self.ctypes.cast(hwnd, self.ctypes.c_void_p).value
        return str(int(value or 0))

    def _describe(self, hwnd) -> dict[str, object] | None:
        if not self.user32.IsWindow(hwnd) or not self.user32.IsWindowVisible(hwnd):
            return None
        title_length = self.user32.GetWindowTextLengthW(hwnd)
        if title_length <= 0 or title_length > 4096:
            return None
        title_buffer = self.ctypes.create_unicode_buffer(title_length + 1)
        if self.user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer)) <= 0:
            return None
        class_buffer = self.ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(hwnd, class_buffer, len(class_buffer))
        process_id = self.wintypes.DWORD()
        self.user32.GetWindowThreadProcessId(hwnd, self.ctypes.byref(process_id))
        rect = self.wintypes.RECT()
        has_rect = bool(self.user32.GetWindowRect(hwnd, self.ctypes.byref(rect)))
        foreground = self.user32.GetForegroundWindow()
        window_id = self._window_id(hwnd)
        return {
            "window_id": window_id,
            "title": title_buffer.value,
            "class_name": class_buffer.value,
            "process_id": int(process_id.value),
            "foreground": window_id == self._window_id(foreground),
            "minimized": bool(self.user32.IsIconic(hwnd)),
            "bounds": (
                {
                    "left": int(rect.left),
                    "top": int(rect.top),
                    "right": int(rect.right),
                    "bottom": int(rect.bottom),
                }
                if has_rect
                else None
            ),
        }

    def list_windows(self, max_results: int) -> list[dict[str, object]]:
        if isinstance(max_results, bool) or not isinstance(max_results, int):
            raise BrokerPolicyViolation("max_results must be an integer")
        if max_results < 1 or max_results > 200:
            raise BrokerPolicyViolation("max_results must be from 1 to 200")
        windows: list[dict[str, object]] = []

        @self.callback_type
        def callback(hwnd, _lparam):
            try:
                item = self._describe(hwnd)
                if item is not None:
                    windows.append(item)
            except (OSError, ValueError):
                pass
            return len(windows) < max_results

        self.user32.EnumWindows(callback, 0)
        return windows[:max_results]

    def foreground_window(self) -> dict[str, object] | None:
        hwnd = self.user32.GetForegroundWindow()
        if not hwnd:
            return None
        return self._describe(hwnd)

    def launch(self, executable: Path) -> int:
        process = subprocess.Popen(
            [str(executable)],
            cwd=str(executable.parent),
            shell=False,
            close_fds=True,
        )
        return int(process.pid)

    def focus(self, window_id: str) -> dict[str, object]:
        hwnd = self._hwnd(window_id)
        if not self.user32.IsWindow(hwnd):
            raise BrokerPolicyViolation("The requested window no longer exists")
        if self.user32.IsIconic(hwnd):
            self.user32.ShowWindowAsync(hwnd, 9)  # SW_RESTORE
        requested = bool(self.user32.SetForegroundWindow(hwnd))
        time.sleep(0.12)
        foreground = self.user32.GetForegroundWindow()
        foreground_id = self._window_id(foreground) if foreground else None
        return {
            "window_id": window_id,
            "focus_requested": requested,
            "focused": foreground_id == window_id,
            "foreground_window_id": foreground_id,
        }


class WindowsDesktopOperator:
    """Functionality-first Windows observation and allowlisted app control."""

    def __init__(
        self,
        apps: WindowsAppStore,
        backend: WindowsBackend,
        audit_path: Path | None = None,
    ):
        self.apps = apps
        self.backend = backend
        self.audit = MetadataAuditLog(audit_path)

    def status(self) -> dict[str, object]:
        records = self.apps.load()
        result = {
            "mode": "allowlisted-windows-control",
            "available": True,
            "registered_apps": len(records),
            "can_list_top_level_windows": True,
            "can_observe_foreground_window": True,
            "can_launch_registered_apps": True,
            "can_focus_existing_windows": True,
            "arbitrary_commands": False,
            "arbitrary_arguments": False,
            "keyboard_input": False,
            "mouse_input": False,
            "screen_capture": False,
            "process_termination": False,
            "administrator_access": False,
        }
        self.audit.record("windows_status", "[desktop]", True, apps=len(records))
        return result

    def list_apps(self) -> dict[str, object]:
        records = self.apps.load()
        result = {
            "apps": [
                {
                    "app_id": record.app_id,
                    "display_name": record.display_name,
                    "executable": str(record.executable),
                    "app_user_model_id": record.app_user_model_id,
                    "allow_text_entry": record.allow_text_entry,
                }
                for record in records
            ],
            "count": len(records),
        }
        self.audit.record("windows_list_apps", "[apps]", True, count=len(records))
        return result

    def list_windows(self, max_results: int = 50) -> dict[str, object]:
        windows = self.backend.list_windows(max_results)
        result = {"windows": windows, "count": len(windows), "truncated": len(windows) >= max_results}
        self.audit.record("windows_list_windows", "[desktop]", True, count=len(windows))
        return result

    def foreground_window(self) -> dict[str, object]:
        window = self.backend.foreground_window()
        self.audit.record(
            "windows_foreground_window",
            "[desktop]",
            True,
            observed=window is not None,
        )
        return {"window": window, "observed": window is not None}

    def launch_app(self, app_id: str) -> dict[str, object]:
        validated_id = self.apps.validate_app_id(app_id)
        records = {record.app_id: record for record in self.apps.load()}
        record = records.get(validated_id)
        if record is None:
            raise BrokerPolicyViolation(f"Unknown registered Windows app: {validated_id}")
        process_id = self.backend.launch(record.executable)
        observed: dict[str, object] | None = None
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            observed = next(
                (
                    window
                    for window in self.backend.list_windows(200)
                    if window.get("process_id") == process_id
                ),
                None,
            )
            if observed is not None:
                break
            time.sleep(0.1)
        result = {
            "app_id": record.app_id,
            "display_name": record.display_name,
            "launch_requested": True,
            "process_id": process_id,
            "window_observed": observed is not None,
            "window": observed,
        }
        self.audit.record(
            "windows_launch_app",
            "[app]",
            True,
            app_id=record.app_id,
            process_id=process_id,
            window_observed=observed is not None,
        )
        return result

    def focus_window(self, window_id: str) -> dict[str, object]:
        if not isinstance(window_id, str) or not WINDOW_ID_PATTERN.fullmatch(window_id):
            raise BrokerPolicyViolation("window_id must be a positive decimal window handle")
        result = self.backend.focus(window_id)
        self.audit.record(
            "windows_focus_window",
            "[desktop]",
            bool(result.get("focused")),
            window_id=window_id,
            focus_requested=bool(result.get("focus_requested")),
        )
        return result
