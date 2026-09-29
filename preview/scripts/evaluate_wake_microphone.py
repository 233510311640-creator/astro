"""Interactive, metadata-only acceptance check for the preview wake listener.

Pause Cypher's installed activation in its tray before running this script so
the two listeners do not compete for the microphone. This never transcribes,
stores, or dispatches captured commands. The worker's audio payload is dropped.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import winsound


WORKER = Path(__file__).resolve().parents[1] / "src" / "local_assistant" / "wake_worker.py"
ERRORS = {
    "MODEL_MISSING", "DEPENDENCY_MISSING", "TUNING_INVALID",
    "INPUT_UNAVAILABLE", "INPUT_OVERFLOW", "AUDIO_LIMIT", "WORKER_FAILURE",
}


def settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise ValueError("LOCALAPPDATA is unavailable")
    return Path(base) / "Cypher" / "CorePreview" / "host_config.json"


def worker_command(settings: dict, worker: Path = WORKER,
                   candidate_model: Path | None = None) -> list[str]:
    python = Path(str(settings.get("wake_python_path", "")))
    model = candidate_model if candidate_model is not None else Path(str(settings.get("wake_model_path", "")))
    deps = Path(str(settings.get("wake_deps_path", "")))
    if not (python.is_file() and (model / "tokens.txt").is_file()
            and (deps / "sherpa_onnx" / "__init__.py").is_file()
            and worker.is_file()):
        raise ValueError("The installed wake runtime or preview worker is missing")
    score = float(settings.get("wake_phrase_score", 1.0))
    threshold = float(settings.get("wake_phrase_threshold", 0.25))
    if not (0.5 <= score <= 2.0 and 0.15 <= threshold <= 0.8):
        raise ValueError("Wake phrase tuning is out of range")
    command = [str(python), "-I", "-B", str(worker), "--model-dir", str(model),
               "--deps-dir", str(deps), "--score", f"{score:.2f}",
               "--threshold", f"{threshold:.2f}"]
    device = str(settings.get("wake_device_index", "")).strip()
    name = str(settings.get("wake_device_name", "")).strip()
    api = str(settings.get("wake_host_api", "")).strip()
    if name and len(name) <= 200 and api and len(api) <= 200:
        command.extend(["--device-name-b64", base64.b64encode(name.encode("utf-8")).decode("ascii"),
                        "--host-api-b64", base64.b64encode(api.encode("utf-8")).decode("ascii")])
    elif name or api:
        raise ValueError("Wake microphone selector is invalid")
    elif device:
        if not device.isascii() or not device.isdecimal() or int(device) > 128:
            raise ValueError("Wake microphone index is invalid")
        command.extend(["--device", device])
    return command


class WorkerSession:
    def __init__(self, command: list[str]):
        env = dict(os.environ)
        env["HF_HUB_OFFLINE"] = "1"
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE,
                                        stderr=subprocess.DEVNULL, text=True,
                                        encoding="ascii", errors="replace",
                                        bufsize=1, env=env)
        self.messages: queue.Queue[str] = queue.Queue(maxsize=32)
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            # Never copy WAV or cloud chunks to the queue or logs.
            if line.startswith(("AUDIO ", "CHUNK ")):
                continue
            # Device identity and a quiet-room notice are diagnostic metadata,
            # not a failed detection or a reason to stop the acceptance run.
            if line.startswith("DEVICE ") or line.strip() == "SILENT":
                continue
            marker = line.strip()
            if marker not in {"READY", "SIGNAL", "WAKE", "STOP", "NO_SPEECH"}:
                if marker.startswith("ERROR "):
                    code = marker[6:]
                    marker = "ERROR " + (code if code in ERRORS else "PROTOCOL_ERROR")
                else:
                    marker = "ERROR PROTOCOL_ERROR"
            try:
                self.messages.put_nowait(marker)
            except queue.Full:
                pass
        try:
            self.messages.put_nowait("EXIT")
        except queue.Full:
            pass

    def next(self, seconds: float) -> str | None:
        try:
            return self.messages.get(timeout=max(0.01, seconds))
        except queue.Empty:
            return None

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=2)
        if self.process.stdout is not None:
            self.process.stdout.close()


class VisualCue:
    """Visible, user-acknowledged cue for a supervised acceptance run."""

    def __init__(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Cypher wake-word test")
        self.root.geometry("640x260")
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#151515")
        self.ready = False
        self.closed = False
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.label = tk.Label(
            self.root, text="Click BEGIN when you are ready to speak.\n"
            "No recordings or commands are saved or sent.",
            bg="#151515", fg="white", font=("Segoe UI", 18),
            wraplength=580, justify="center",
        )
        self.label.pack(expand=True, padx=20, pady=15)
        self.button = tk.Button(
            self.root, text="BEGIN", command=self.begin,
            font=("Segoe UI", 14), width=12,
        )
        self.button.pack(pady=(0, 25))
        self.root.update()

    def begin(self):
        self.ready = True
        self.button.pack_forget()

    def close(self):
        self.closed = True
        self.root.destroy()

    def update(self, message: str | None = None):
        if self.closed:
            raise KeyboardInterrupt
        if message is not None:
            self.label.configure(text=message)
        try:
            self.root.update()
        except Exception as exc:
            self.closed = True
            raise KeyboardInterrupt from exc

    def wait_for_begin(self, timeout_seconds: int = 120) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while not self.ready:
            if time.monotonic() >= deadline:
                self.close()
                return False
            self.update()
            time.sleep(0.05)
        return True

    def pause(self, seconds: float):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.update()
            time.sleep(min(0.05, deadline - time.monotonic()))


def wait_for_ready(session: WorkerSession, visual: VisualCue | None = None) -> str:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if visual:
            visual.update()
        marker = session.next(min(0.1 if visual else 20, deadline - time.monotonic()))
        if marker == "READY":
            return marker
        if marker and (marker.startswith("ERROR ") or marker == "EXIT"):
            return marker
    return "ERROR STARTUP_TIMEOUT"


def attempts(command: list[str], count: int, auto_cue: bool = False,
             visual: VisualCue | None = None) -> int:
    detections = 0
    failures = 0
    signal_attempts = 0
    for number in range(1, count + 1):
        session = WorkerSession(command)
        try:
            if visual:
                visual.update(f"Attempt {number}/{count}\nStarting listener...")
            ready = wait_for_ready(session, visual)
            if ready != "READY":
                failures += 1
                print(f"Attempt {number}: listener unavailable ({ready})")
                if visual:
                    visual.update(f"Attempt {number}/{count}: listener unavailable\n{ready}")
                    visual.pause(0.7)
                continue
            phrase = "Cypher" if number % 2 else "Hello Cypher"
            if visual:
                visual.update(f"Attempt {number}/{count}\nSPEAK NOW: {phrase}, status")
                winsound.MessageBeep()
            elif auto_cue:
                print(f"Attempt {number}/{count}: after the tone, say '{phrase}, status' clearly.", flush=True)
                winsound.Beep(700, 100)
                time.sleep(0.25)
            else:
                input(f"Attempt {number}/{count}: press Enter, then say '{phrase}, status' clearly. ")
            deadline = time.monotonic() + 10
            result = "MISSED"
            signal_seen = False
            while time.monotonic() < deadline:
                if visual:
                    visual.update()
                marker = session.next(min(0.1 if visual else 10, deadline - time.monotonic()))
                if marker == "SIGNAL":
                    signal_seen = True
                if marker == "WAKE":
                    result = "DETECTED"
                    detections += 1
                    break
                if marker and (marker.startswith("ERROR ") or marker in {"EXIT", "STOP"}):
                    result = marker
                    failures += 1
                    break
            if signal_seen:
                signal_attempts += 1
            print(f"Attempt {number}: {result}; microphone signal {'seen' if signal_seen else 'not seen'}")
            if visual:
                visual.update(f"Attempt {number}/{count}: {result}\n"
                              f"Microphone signal: {'SEEN' if signal_seen else 'NOT SEEN'}\n"
                              "Next cue in a moment...")
                visual.pause(0.6)
        finally:
            session.close()
    required = (19 if count == 20 else count)
    print(f"Detected {detections}/{count}; microphone signal on {signal_attempts}/{count}; "
          f"required {required}. Listener errors: {failures}.")
    if visual:
        visual.update(f"Test complete: {detections}/{count} detected.\n"
                      f"Microphone signal: {signal_attempts}/{count}.\n"
                      f"Required: {required}; listener errors: {failures}.")
        try:
            visual.pause(8)
        except KeyboardInterrupt:
            pass
    return 0 if detections >= required and failures == 0 else 1


def background(command: list[str], duration: int) -> int:
    deadline = time.monotonic() + duration
    false_wakes = 0
    errors = 0
    consecutive_errors = 0
    print("Background check running. Do not say the wake phrase. Ctrl+C stops it early.")
    while time.monotonic() < deadline:
        session = WorkerSession(command)
        try:
            ready = wait_for_ready(session)
            if ready != "READY":
                errors += 1
                consecutive_errors += 1
                print(f"Listener unavailable: {ready}")
            else:
                consecutive_errors = 0
                while time.monotonic() < deadline:
                    marker = session.next(min(1, deadline - time.monotonic()))
                    if marker in {None, "SIGNAL"}:
                        continue
                    if marker in {"WAKE", "STOP"}:
                        false_wakes += 1
                        print(f"Unexpected wake event #{false_wakes}; no command was sent")
                        break
                    if marker.startswith("ERROR ") or marker == "EXIT":
                        errors += 1
                        consecutive_errors += 1
                        print(f"Listener stopped: {marker}")
                        break
        finally:
            session.close()
        if consecutive_errors >= 5:
            print("Stopped after five consecutive listener failures.")
            return 1
        if time.monotonic() < deadline:
            time.sleep(1)
    print(f"Background result: {false_wakes} unexpected wakes, {errors} listener errors.")
    return 0 if false_wakes == 0 and errors == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("attempts", "background"))
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--auto-cue", action="store_true",
                        help="give a short audible cue for each attempt instead of requiring Enter")
    parser.add_argument("--visual-cue", action="store_true",
                        help="show a visible Begin button and SPEAK NOW prompts")
    parser.add_argument("--duration-minutes", type=int, default=120)
    parser.add_argument("--start-delay", type=int, default=0,
                        help="seconds to wait before the first attempt (0-30)")
    parser.add_argument("--listener-paused", action="store_true",
                        help="confirm that installed Cypher activation is paused in its tray")
    parser.add_argument("--candidate-model", type=Path,
                        help="use an unpacked offline model for this test only; installed settings stay unchanged")
    args = parser.parse_args()
    if args.visual_cue and args.mode != "attempts":
        parser.error("Visible cues are only for spoken wake attempts")
    if not args.listener_paused:
        parser.error("Pause installed Cypher activation first, then add --listener-paused")
    if not (1 <= args.attempts <= 100 and 1 <= args.duration_minutes <= 720 and 0 <= args.start_delay <= 30):
        parser.error("Attempt count or background duration is out of range")
    try:
        settings = json.loads(settings_path().read_text(encoding="utf-8-sig"))
        command = worker_command(settings, candidate_model=args.candidate_model)
        visual = VisualCue() if args.visual_cue else None
        if visual:
            print("Waiting for the visible BEGIN button; no attempts have started.", flush=True)
            if not visual.wait_for_begin():
                print("No test started: BEGIN was not clicked within two minutes.")
                return 3
        elif args.start_delay:
            print(f"Starting in {args.start_delay} seconds. Speak only after each short tone.", flush=True)
            time.sleep(args.start_delay)
        return attempts(command, args.attempts, args.auto_cue, visual) if args.mode == "attempts" else background(command, args.duration_minutes * 60)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        # Do not print file contents, device names, audio, or untrusted errors.
        print("Wake evaluation setup failed. Check the installed offline runtime and selected microphone.")
        return 2
    except KeyboardInterrupt:
        print("Wake evaluation stopped early; acceptance is incomplete.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
