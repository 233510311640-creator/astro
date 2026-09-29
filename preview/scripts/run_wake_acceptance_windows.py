"""Supervised wake acceptance with automatic installed-host restoration.

This runner never transcribes, saves, or dispatches microphone audio. It
temporarily stops the installed Cypher host so the preview and installed
listeners cannot compete for the input device. A host that is working on a
task is never stopped by this runner.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts" / "manage_cypher_core_preview_windows.ps1"
EVALUATOR = ROOT / "scripts" / "evaluate_wake_microphone.py"
STATUS_PATTERN = re.compile(r"^Cypher Core Preview: ([a-z_]+)$", re.MULTILINE)


class AcceptanceSetupError(RuntimeError):
    pass


def manager_status() -> str:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(MANAGER), "status"],
            capture_output=True, text=True, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptanceSetupError("Cypher's installed status could not be verified.") from exc
    match = STATUS_PATTERN.search(result.stdout)
    if result.returncode != 0 or match is None:
        raise AcceptanceSetupError("Cypher's installed status could not be verified.")
    return match.group(1)


def manager_action(action: str) -> None:
    if action not in {"stop", "start"}:
        raise ValueError("Invalid manager action")
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-ExecutionPolicy", "Bypass", "-File", str(MANAGER), action],
            capture_output=True, text=True, timeout=35, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptanceSetupError(f"Cypher could not {action} safely.") from exc
    if result.returncode != 0:
        raise AcceptanceSetupError(f"Cypher could not {action} safely.")


def host_process_count() -> int:
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive",
             "-Command", "@(Get-Process -Name CypherCoreHost -ErrorAction SilentlyContinue).Count"],
            capture_output=True, text=True, timeout=15, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AcceptanceSetupError("Cypher's process state could not be verified.") from exc
    value = result.stdout.strip()
    if result.returncode != 0 or not value.isascii() or not value.isdecimal():
        raise AcceptanceSetupError("Cypher's process state could not be verified.")
    return int(value)


def wait_until_ready(seconds: int = 25) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if manager_status() == "ready" and host_process_count() > 0:
            return
        time.sleep(1)
    raise AcceptanceSetupError(
        "Cypher restart was requested, but READY was not confirmed. "
        "Check Cypher in the tray or start it from its shortcut."
    )


def restore_installed() -> None:
    state = manager_status()
    running = host_process_count() > 0
    if state == "stopped" and not running:
        manager_action("start")
        wait_until_ready()
        print("Installed Cypher is READY again.", flush=True)
    elif state in {"ready", "working", "paused"} and running:
        print("Installed Cypher remained running.", flush=True)
    else:
        raise AcceptanceSetupError(
            "Cypher's restart state is uncertain. Check its tray or start it from its shortcut."
        )


def managed_test(run_test: Callable[[], int]) -> int:
    initial = manager_status()
    if initial == "working":
        raise AcceptanceSetupError("Cypher is handling a task. Finish or stop that task before a microphone test.")
    if initial not in {"ready", "stopped"}:
        raise AcceptanceSetupError("Cypher must be READY or already stopped before a microphone test.")
    restore = initial == "ready"
    try:
        if restore:
            print("Pausing installed Cypher for the microphone test...", flush=True)
            manager_action("stop")
        if manager_status() != "stopped" or host_process_count() != 0:
            raise AcceptanceSetupError("The installed listener did not fully stop; no microphone test was started.")
        return run_test()
    finally:
        if restore:
            print("Restoring installed Cypher...", flush=True)
            restore_installed()


def confirm_pause() -> bool:
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        return bool(messagebox.askokcancel(
            "Cypher wake-word test",
            "Finish any task, MIC recording, or spoken reply first. "
            "The installed Cypher will pause during this no-action microphone test "
            "and restart afterward. Continue?",
            parent=root,
        ))
    finally:
        root.destroy()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("attempts", "background"), nargs="?", default="attempts")
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--duration-minutes", type=int, default=120)
    parser.add_argument("--candidate-model", type=Path,
                        help="use an unpacked offline model for this test only")
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This supervised runner requires Windows")
    if not (1 <= args.attempts <= 100 and 1 <= args.duration_minutes <= 720):
        parser.error("Attempt count or duration is out of range")
    if not MANAGER.is_file() or not EVALUATOR.is_file():
        parser.error("The preview manager or evaluator is missing")
    if args.candidate_model is not None and not (args.candidate_model / "tokens.txt").is_file():
        parser.error("The candidate model is missing its tokens file")

    def evaluate() -> int:
        command = [sys.executable, str(EVALUATOR), args.mode, "--listener-paused"]
        if args.candidate_model is not None:
            command.extend(["--candidate-model", str(args.candidate_model.resolve())])
        if args.mode == "attempts":
            command.extend(["--visual-cue", "--attempts", str(args.attempts)])
        else:
            command.extend(["--duration-minutes", str(args.duration_minutes)])
        return subprocess.run(command, check=False).returncode

    try:
        if not confirm_pause():
            print("Wake acceptance was cancelled before Cypher was paused.")
            return 3
        return managed_test(evaluate)
    except AcceptanceSetupError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Wake acceptance was interrupted; installed Cypher restoration was attempted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
