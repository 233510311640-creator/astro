from pathlib import Path
import re
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_hermes_windows.ps1"


class HermesAuditScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCRIPT.read_text(encoding="utf-8")
        cls.normalized = cls.source.lower()

    def test_audit_is_read_only_and_has_no_install_or_mutation_commands(self):
        prohibited = (
            "set-content",
            "add-content",
            "out-file",
            "new-item",
            "remove-item",
            "move-item",
            "copy-item",
            "set-itemproperty",
            "start-process",
            "invoke-expression",
            "iex ",
            "winget ",
            "pip install",
            "npm install",
            "hermes setup",
            "hermes model",
        )
        for value in prohibited:
            with self.subTest(value=value):
                self.assertNotIn(value, self.normalized)

    def test_only_loopback_http_endpoint_is_present(self):
        urls = re.findall(r"https?://[^\s\"']+", self.source)
        self.assertEqual(urls, ["http://127.0.0.1:11434/api/version"])

    def test_script_does_not_read_known_secret_or_content_files(self):
        prohibited = (
            ".env",
            "config.yaml",
            "memory.md",
            "user.md",
            "cookies",
            "login data",
            "credentials",
        )
        command_lines = [
            line.lower()
            for line in self.source.splitlines()
            if not line.lstrip().lower().startswith("write-host")
        ]
        executable_text = "\n".join(command_lines)
        for value in prohibited:
            with self.subTest(value=value):
                self.assertNotIn(value, executable_text)

    def test_ollama_exposure_and_model_checks_are_present(self):
        required = (
            "get-nettcpconnection",
            "local-assistant-brain:latest",
            '@("list")',
            '@("ps")',
            "test-isloopbackaddress",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, self.normalized)

    def test_windows_powershell_compatible_failure_count_expression(self):
        self.assertNotRegex(
            self.normalized,
            r"if\s*\(\s*@\([^\n]*where-object[^\n]*\}\)\.count",
        )
        self.assertIn(
            '$failedfindings = @($findings | where-object { $_.status -eq "fail" })',
            self.normalized,
        )
        self.assertIn("if ($failedfindings.count -gt 0)", self.normalized)

    def test_native_commands_have_progress_and_hard_timeouts(self):
        required = (
            "function write-auditstep",
            "[check]",
            "timeoutseconds",
            "waitforexit",
            "$process.kill()",
            "timedout",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, self.normalized)
        self.assertNotIn("& $commandpath", self.normalized)

    def test_model_check_reuses_inventory_instead_of_extra_show_command(self):
        self.assertIn(
            '$ollamalist.output -match "(?m)^local-assistant-brain(?::latest)?\\s"',
            self.normalized,
        )
        self.assertNotIn('@("show", "local-assistant-brain:latest")', self.normalized)

    def test_delimiter_counts_are_balanced(self):
        self.assertEqual(self.source.count("{"), self.source.count("}"))
        self.assertEqual(self.source.count("("), self.source.count(")"))
        self.assertEqual(self.source.count("["), self.source.count("]"))


if __name__ == "__main__":
    unittest.main()
