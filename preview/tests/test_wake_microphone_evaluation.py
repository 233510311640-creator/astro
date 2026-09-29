"""Safety checks for the opt-in real-microphone acceptance helper."""

from pathlib import Path
import importlib.util
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_wake_microphone.py"
spec = importlib.util.spec_from_file_location("evaluate_wake_microphone", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WakeMicrophoneEvaluationTests(unittest.TestCase):
    def test_rejects_missing_runtime_without_launch(self):
        with self.assertRaises(ValueError):
            module.worker_command({"wake_python_path": "Z:/missing/python.exe"})

    def test_audio_payload_never_queued_or_printed(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('line.startswith(("AUDIO ", "CHUNK "))', source)
        self.assertNotIn("print(line)", source)
        self.assertNotIn("read_bytes()", source)
        self.assertNotIn("write_bytes(", source)

    def test_requires_explicit_pause_confirmation(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--listener-paused", source)
        self.assertIn("Pause installed Cypher activation first", source)

    def test_visual_run_waits_for_user_and_shows_prompt(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--visual-cue", source)
        self.assertIn("visual.wait_for_begin()", source)
        self.assertIn("SPEAK NOW: {phrase}, status", source)
        self.assertIn("if time.monotonic() >= deadline:", source)

    def test_attempts_report_signal_without_retaining_audio(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('if marker == "SIGNAL":', source)
        self.assertIn("microphone signal on {signal_attempts}/{count}", source)
        self.assertIn('line.startswith(("AUDIO ", "CHUNK "))', source)

    def test_candidate_model_overrides_settings_only_for_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            python, deps, installed, candidate, worker = (
                root / "python.exe", root / "deps", root / "installed", root / "candidate", root / "worker.py")
            deps.joinpath("sherpa_onnx").mkdir(parents=True)
            installed.mkdir()
            candidate.mkdir()
            for path in (python, worker, deps / "sherpa_onnx" / "__init__.py",
                         installed / "tokens.txt", candidate / "tokens.txt"):
                path.touch()
            settings = {"wake_python_path": str(python), "wake_deps_path": str(deps),
                        "wake_model_path": str(installed)}
            command = module.worker_command(settings, worker=worker, candidate_model=candidate)
            self.assertEqual(command[command.index("--model-dir") + 1], str(candidate))
            self.assertEqual(settings["wake_model_path"], str(installed))


if __name__ == "__main__":
    unittest.main()
