"""The installed manager must read live ISO heartbeats under non-US locales."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


MANAGER = Path(__file__).parents[1] / "scripts" / "manage_cypher_core_preview_windows.ps1"


@unittest.skipUnless(sys.platform == "win32", "Windows PowerShell test")
class PowerShellHeartbeatTests(unittest.TestCase):
    def test_status_uses_live_datetime_without_locale_reparse(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch) / "Cypher" / "CorePreview"
            install.mkdir(parents=True)
            heartbeat = install / "heartbeat.json"
            (install / "host_config.json").write_text(
                json.dumps({"wake_word_enabled": True}), encoding="utf-8"
            )
            env = dict(os.environ, LOCALAPPDATA=scratch)

            def status_at(timestamp):
                heartbeat.write_text(json.dumps({
                    "timestamp": timestamp.isoformat(), "pid": 12345,
                    "status": "ready", "version": "test",
                }), encoding="utf-8")
                command = (
                    "[Threading.Thread]::CurrentThread.CurrentCulture = "
                    "[Globalization.CultureInfo]'en-IN'; "
                    f"& '{str(MANAGER).replace(chr(39), chr(39) * 2)}' status"
                )
                result = subprocess.run(
                    ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-Command", command], env=env, capture_output=True,
                    text=True, timeout=20, check=True,
                )
                return result.stdout

            now = datetime.now(timezone.utc)
            self.assertIn("Cypher Core Preview: ready", status_at(now))
            self.assertIn("Wake word configured: enabled", status_at(now))
            self.assertIn("Cypher Core Preview: stopped", status_at(now - timedelta(minutes=1)))
            self.assertIn("Cypher Core Preview: stopped", status_at(now + timedelta(minutes=1)))

    def test_stop_refuses_active_work_without_creating_request(self):
        with tempfile.TemporaryDirectory() as scratch:
            install = Path(scratch) / "Cypher" / "CorePreview"
            install.mkdir(parents=True)
            (install / "heartbeat.json").write_text(json.dumps({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pid": 12345, "status": "working", "version": "test",
            }), encoding="utf-8")
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(MANAGER), "stop"],
                env=dict(os.environ, LOCALAPPDATA=scratch),
                capture_output=True, text=True, timeout=20, check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertFalse((install / "stop.request").exists())


if __name__ == "__main__":
    unittest.main()
