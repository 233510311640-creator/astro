from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from local_assistant.broker_mcp import McpApplication
from local_assistant.capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker
from local_assistant.windows_operator import (
    NativeWindowsBackend,
    WindowsAppStore,
    WindowsDesktopOperator,
)


class FakeWindowsBackend:
    def __init__(self):
        self.windows = [
            {
                "window_id": "99",
                "title": "Private document name",
                "class_name": "FakeWindow",
                "process_id": 123,
                "foreground": True,
                "minimized": False,
                "bounds": {"left": 1, "top": 2, "right": 401, "bottom": 302},
            }
        ]
        self.launched = []
        self.focused = []

    def list_windows(self, max_results: int):
        if max_results < 1 or max_results > 200:
            raise BrokerPolicyViolation("max_results must be from 1 to 200")
        return self.windows[:max_results]

    def foreground_window(self):
        return self.windows[0]

    def launch(self, executable: Path):
        self.launched.append(executable)
        return 123

    def focus(self, window_id: str):
        self.focused.append(window_id)
        return {
            "window_id": window_id,
            "focus_requested": True,
            "focused": window_id == "99",
            "foreground_window_id": "99",
        }


class WindowsOperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.config = self.base / "data" / "windows_apps.json"
        self.audit = self.base / "data" / "audit.jsonl"
        self.app = self.base / "Example App.exe"
        self.app.write_bytes(b"MZ-test")
        self.store = WindowsAppStore(self.config)
        self.store.add("example", "Example App", self.app)
        self.backend = FakeWindowsBackend()
        self.operator = WindowsDesktopOperator(self.store, self.backend, self.audit)

    def tearDown(self):
        self.temp.cleanup()

    def test_store_round_trip_and_strict_shape(self):
        records = self.store.load()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].app_id, "example")
        self.assertIsNone(records[0].app_user_model_id)
        self.assertFalse(records[0].allow_text_entry)
        payload = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], 2)
        self.assertEqual(
            set(payload["apps"][0]),
            {
                "id",
                "display_name",
                "executable",
                "added_at",
                "app_user_model_id",
                "allow_text_entry",
            },
        )
        payload["unexpected"] = True
        self.config.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.store.load()

    def test_version_one_registry_migrates_without_granting_text_entry(self):
        payload = json.loads(self.config.read_text(encoding="utf-8"))
        payload["version"] = 1
        for item in payload["apps"]:
            item.pop("app_user_model_id")
            item.pop("allow_text_entry")
        self.config.write_text(json.dumps(payload), encoding="utf-8")
        loaded = self.store.load()
        self.assertFalse(loaded[0].allow_text_entry)
        self.assertIsNone(loaded[0].app_user_model_id)
        changed = self.store.set_text_entry("example", True)
        self.assertTrue(changed.allow_text_entry)
        migrated = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(migrated["version"], 2)

    def test_packaged_identity_and_text_entry_are_independent_permissions(self):
        identity = "Microsoft.Example_8wekyb3d8bbwe!App"
        changed = self.store.set_app_user_model_id("example", identity)
        self.assertEqual(changed.app_user_model_id, identity)
        self.assertFalse(changed.allow_text_entry)
        changed = self.store.set_text_entry("example", True)
        self.assertTrue(changed.allow_text_entry)
        self.assertEqual(changed.app_user_model_id, identity)
        with self.assertRaises(BrokerPolicyViolation):
            self.store.set_app_user_model_id("example", "invalid identity with spaces")

    def test_store_rejects_non_executable_relative_and_duplicate_targets(self):
        text = self.base / "readme.txt"
        text.write_text("no", encoding="utf-8")
        with self.assertRaises(BrokerPolicyViolation):
            self.store.validate_executable(text)
        with self.assertRaises(BrokerPolicyViolation):
            self.store.validate_executable(Path("relative.exe"))
        with self.assertRaises(BrokerPolicyViolation):
            self.store.add("duplicate", "Duplicate", self.app)

    def test_builtin_seed_registers_only_existing_exact_executables(self):
        windows = self.base / "Windows"
        system32 = windows / "System32"
        system32.mkdir(parents=True)
        for name in ("notepad.exe", "calc.exe"):
            (system32 / name).write_bytes(b"MZ")
        seeded = WindowsAppStore(
            self.base / "seeded.json", environment={"WINDIR": str(windows)}
        )
        result = seeded.seed_builtin_apps(
            start_apps={
                "Notepad": "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
                "Calculator": "Microsoft.WindowsCalculator_8wekyb3d8bbwe!App",
            }
        )
        self.assertEqual(result["added"], ["notepad", "calculator"])
        self.assertEqual(result["unavailable"], ["paint", "file-explorer"])
        records = {record.app_id: record for record in seeded.load()}
        self.assertEqual(sorted(records), ["calculator", "notepad"])
        self.assertEqual(
            records["notepad"].app_user_model_id,
            "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App",
        )
        self.assertFalse(records["notepad"].allow_text_entry)
        self.assertFalse(records["calculator"].allow_text_entry)

    def test_builtin_seed_rejects_discovered_identity_already_bound_to_another_app(self):
        windows = self.base / "Windows"
        system32 = windows / "System32"
        system32.mkdir(parents=True)
        notepad = system32 / "notepad.exe"
        notepad.write_bytes(b"MZ")
        other = self.base / "Other.exe"
        other.write_bytes(b"MZ")
        identity = "Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"
        seeded = WindowsAppStore(
            self.base / "seed-conflict.json", environment={"WINDIR": str(windows)}
        )
        seeded.add("other", "Other", other, app_user_model_id=identity)
        with self.assertRaises(BrokerPolicyViolation):
            seeded.seed_builtin_apps(start_apps={"Notepad": identity})

    def test_observation_launch_and_focus_are_truthful(self):
        status = self.operator.status()
        self.assertFalse(status["keyboard_input"])
        self.assertFalse(status["arbitrary_commands"])
        listed = self.operator.list_windows(10)
        self.assertEqual(listed["windows"][0]["window_id"], "99")
        foreground = self.operator.foreground_window()
        self.assertTrue(foreground["observed"])
        launched = self.operator.launch_app("example")
        self.assertTrue(launched["window_observed"])
        self.assertEqual(self.backend.launched, [self.app.resolve()])
        focused = self.operator.focus_window("98")
        self.assertFalse(focused["focused"])

    def test_window_titles_are_not_written_to_audit(self):
        self.operator.list_windows()
        text = self.audit.read_text(encoding="utf-8")
        self.assertNotIn("Private document name", text)
        self.assertIn("windows_list_windows", text)

    def test_mcp_adds_only_six_windows_tools_when_configured(self):
        sandbox = self.base / "Sandbox"
        sandbox.mkdir()
        broker = ReadOnlyCapabilityBroker(sandbox, self.audit)
        base = McpApplication(broker).dispatch(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
        )
        configured_app = McpApplication(broker, windows=self.operator)
        configured = configured_app.dispatch(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        self.assertEqual(len(base["result"]["tools"]), 22)
        self.assertEqual(len(configured["result"]["tools"]), 28)
        names = {tool["name"] for tool in configured["result"]["tools"]}
        self.assertIn("windows_launch_app", names)
        self.assertIn("windows_focus_window", names)

        listed = configured_app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 30,
                "method": "tools/call",
                "params": {"name": "windows_list_apps", "arguments": {}},
            }
        )
        registered = listed["result"]["structuredContent"]["apps"][0]
        self.assertIn("app_user_model_id", registered)
        self.assertIn("allow_text_entry", registered)

        called = configured_app.dispatch(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "windows_launch_app", "arguments": {"app_id": "example"}},
            }
        )
        self.assertFalse(called["result"]["isError"])
        self.assertTrue(called["result"]["structuredContent"]["launch_requested"])

    def test_mcp_rejects_command_arguments_and_unknown_apps(self):
        sandbox = self.base / "Sandbox"
        sandbox.mkdir()
        app = McpApplication(
            ReadOnlyCapabilityBroker(sandbox, self.audit), windows=self.operator
        )
        cases = (
            {"app_id": "example", "arguments": ["--dangerous"]},
            {"app_id": "unknown"},
        )
        for index, arguments in enumerate(cases, start=1):
            result = app.dispatch(
                {
                    "jsonrpc": "2.0",
                    "id": index,
                    "method": "tools/call",
                    "params": {"name": "windows_launch_app", "arguments": arguments},
                }
            )
            self.assertTrue(result["result"]["isError"])

    def test_native_backend_uses_documented_window_apis_and_verifies_focus(self):
        source = Path(NativeWindowsBackend.__module__.replace(".", "/") + ".py")
        project_source = Path(__file__).parents[1] / "src" / source
        text = project_source.read_text(encoding="utf-8")
        for marker in (
            "EnumWindows",
            "GetForegroundWindow",
            "SetForegroundWindow",
            "ShowWindowAsync",
            'shell=False',
            'foreground_id == window_id',
        ):
            self.assertIn(marker, text)


if __name__ == "__main__":
    unittest.main()
