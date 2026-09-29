import unittest
from pathlib import Path

from local_assistant.model_benchmark import (
    BenchmarkError,
    ChatResult,
    TASKS,
    choose_installed_candidates,
    evaluate_task,
    parse_think,
    parse_tool_arguments,
    summarize_runtime_models,
    summarize_latency_trials,
    validate_loopback_url,
)


ROOT = Path(__file__).resolve().parents[1]


def result(text="", tool_calls=None):
    return ChatResult(
        text=text,
        thinking="",
        tool_calls=tool_calls or [],
        time_to_first_event_ms=1,
        total_ms=2,
        prompt_tokens=3,
        output_tokens=4,
        tokens_per_second=5.0,
        done_reason="stop",
    )


class ModelBenchmarkTests(unittest.TestCase):
    def test_endpoint_is_loopback_only(self):
        self.assertEqual(
            validate_loopback_url("http://127.0.0.1:11434/"),
            "http://127.0.0.1:11434",
        )
        for endpoint in (
            "https://127.0.0.1:11434",
            "http://192.168.1.5:11434",
            "http://example.com",
            "http://user:pass@127.0.0.1:11434",
        ):
            with self.assertRaises(ValueError):
                validate_loopback_url(endpoint)

    def test_tool_arguments_accept_object_or_json_object(self):
        self.assertEqual(parse_tool_arguments({"directory": "."}), {"directory": "."})
        self.assertEqual(parse_tool_arguments('{"directory":"."}'), {"directory": "."})
        self.assertIsNone(parse_tool_arguments("not json"))
        self.assertIsNone(parse_tool_arguments("[]"))

    def test_exact_task_passes_only_exact_text(self):
        task = next(task for task in TASKS if task.name == "exact_instruction")
        self.assertTrue(evaluate_task(task, result("CYPHER_READY"))[0])
        self.assertFalse(evaluate_task(task, result("CYPHER_READY!"))[0])

    def test_negated_task_rejects_tool_calls(self):
        task = next(task for task in TASKS if task.name == "negated_tool_request")
        call = {"function": {"name": "sandbox_list", "arguments": {"directory": "."}}}
        passed, issues = evaluate_task(task, result("A question.", [call]))
        self.assertFalse(passed)
        self.assertIn("called a tool when tools were forbidden", issues)

    def test_expected_tool_and_arguments_are_checked(self):
        task = next(task for task in TASKS if task.name == "valid_read_only_tool")
        good_call = {
            "function": {
                "name": "sandbox_list",
                "arguments": {"directory": "."},
            }
        }
        bad_call = {
            "function": {
                "name": "sandbox_list",
                "arguments": {"directory": ".."},
            }
        }
        self.assertTrue(evaluate_task(task, result(tool_calls=[good_call]))[0])
        self.assertFalse(evaluate_task(task, result(tool_calls=[bad_call]))[0])

    def test_candidates_are_bounded_to_installed_models(self):
        installed = [{"name": "gpt-oss:20b"}, {"name": "qwen3.5:9b"}]
        self.assertEqual(
            choose_installed_candidates(installed, ["qwen3.5:9b"]),
            ["qwen3.5:9b"],
        )
        with self.assertRaises(BenchmarkError):
            choose_installed_candidates(installed, ["missing:model"])

    def test_thinking_modes_are_parsed(self):
        self.assertIs(parse_think("off"), False)
        self.assertIs(parse_think("on"), True)
        self.assertEqual(parse_think("LOW"), "low")

    def test_runtime_metadata_is_bounded_and_calculates_vram_residency(self):
        running = [
            {
                "name": "gpt-oss:20b",
                "size": 12_000,
                "size_vram": 9_000,
                "context_length": 16_384,
                "expires_at": "2026-08-18T12:00:00Z",
                "details": {"private_path": "must not be copied"},
            }
        ]
        summary = summarize_runtime_models(running, "gpt-oss:20b")
        self.assertEqual(summary["vram_residency_percent"], 75.0)
        self.assertEqual(summary["context_length"], 16_384)
        self.assertNotIn("details", summary)
        self.assertIsNone(summarize_runtime_models(running, "missing:model"))

    def test_latency_summary_reports_median_p95_max_and_ignores_errors(self):
        trials = [
            {"task": "a", "passed": True, "time_to_first_event_ms": value, "total_ms": value * 2}
            for value in (10, 20, 30, 40, 50)
        ]
        trials.append({"task": "a", "passed": False, "error": "timeout"})
        summary = summarize_latency_trials(trials)
        self.assertEqual(summary["successful_measurements"], 5)
        self.assertEqual(summary["time_to_first_event"]["median_ms"], 30.0)
        self.assertEqual(summary["time_to_first_event"]["p95_ms"], 50.0)
        self.assertEqual(summary["time_to_first_event"]["max_ms"], 50.0)
        self.assertEqual(summary["by_task"]["a"]["pass_rate"], 1.0)

    def test_windows_preflight_requires_explicit_download_consent(self):
        script = (ROOT / "scripts" / "run_cypher_brain_evaluation_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("DOWNLOAD qwen3.5:9b-q4_K_M", script)
        self.assertIn("ollama", script.lower())
        self.assertIn('"http://127.0.0.1:11434"', script)
        self.assertIn("benchmark_cypher_models_windows.ps1", script)
        for unsafe_text in (
            "Set-ExecutionPolicy",
            'Start-Process -Verb RunAs',
            "hermes config",
            "Remove-Item",
        ):
            self.assertNotIn(unsafe_text, script)

    def test_one_click_launcher_is_process_scoped_and_local(self):
        launcher = (ROOT / "RUN_CYPHER_BRAIN_EVALUATION.cmd").read_text(encoding="utf-8")
        benchmark = (ROOT / "scripts" / "benchmark_cypher_models_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("-ExecutionPolicy Bypass", launcher)
        self.assertIn("run_cypher_brain_evaluation_windows.ps1", launcher)
        self.assertNotIn("Set-ExecutionPolicy", launcher)
        self.assertNotIn("exit $benchmarkExitCode", benchmark)


if __name__ == "__main__":
    unittest.main()
