from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class CypherLocalRuntimeRepairWindowsTests(unittest.TestCase):
    def setUp(self):
        self.script = (
            ROOT / "scripts" / "manage_cypher_local_runtime_windows.ps1"
        ).read_text(encoding="utf-8")

    def test_sets_explicit_local_output_and_context_limits(self):
        self.assertIn('"model.max_tokens"; value = "16384"', self.script)
        self.assertIn('"model.context_length"; value = "65536"', self.script)
        self.assertIn('"model.ollama_num_ctx"; value = "65536"', self.script)
        self.assertIn('"tools.tool_search.enabled"; value = "on"', self.script)
        self.assertIn('"tools.tool_search.listing"; value = "on"', self.script)

    def test_repair_is_transactional_and_rollback_is_exact(self):
        self.assertIn("Get-HermesSettingSnapshot", self.script)
        self.assertIn("Restore-HermesSnapshot", self.script)
        self.assertIn("local-runtime-repair-backup.json", self.script)
        self.assertIn("if ($createdBackup)", self.script)
        self.assertIn("ROLLBACK CYPHER LOCAL RUNTIME", self.script)

    def test_unset_hermes_keys_are_normal_under_windows_powershell_5(self):
        helper = self.script.split("function Read-HermesSetting", 1)[1].split(
            "function Get-HermesSettingSnapshot", 1
        )[0]
        self.assertIn('$ErrorActionPreference = "SilentlyContinue"', helper)
        self.assertIn("$exitCode = $LASTEXITCODE", helper)
        self.assertIn("2>$null", helper)
        self.assertIn("$ErrorActionPreference = $previousPreference", helper)
        snapshot = self.script.split("function Get-HermesSettingSnapshot", 1)[1].split(
            "function Set-HermesSettingChecked", 1
        )[0]
        self.assertIn("Read-HermesSetting -Key $setting.key", snapshot)
        self.assertNotIn("& hermes config get", snapshot)

    def test_pasted_confirmation_is_normalized_and_cancel_is_not_success(self):
        helper = self.script.split("function Normalize-Confirmation", 1)[1].split(
            "function Get-HermesSettingSnapshot", 1
        )[0]
        self.assertIn('"[\\u200B\\uFEFF]"', helper)
        self.assertIn("$normalized.Trim()", helper)
        self.assertIn('"\\s+", " "', helper)
        self.assertIn("ToUpperInvariant", helper)
        self.assertIn(
            "(Normalize-Confirmation -Value $confirmation) -ne \"REPAIR CYPHER LOCAL RUNTIME\"",
            self.script,
        )
        self.assertIn(
            "(Normalize-Confirmation -Value $confirmation) -ne \"ROLLBACK CYPHER LOCAL RUNTIME\"",
            self.script,
        )
        self.assertGreaterEqual(self.script.count("exit 2"), 2)

        repair_wrapper = (ROOT / "REPAIR_CYPHER_LOCAL_RUNTIME.cmd").read_text(
            encoding="utf-8"
        )
        rollback_wrapper = (ROOT / "ROLLBACK_CYPHER_LOCAL_RUNTIME.cmd").read_text(
            encoding="utf-8"
        )
        self.assertIn('if "%CYPHER_EXIT%"=="2"', repair_wrapper)
        self.assertIn("repair was cancelled. No setting changed.", repair_wrapper)
        self.assertIn('if "%CYPHER_EXIT%"=="2"', rollback_wrapper)
        self.assertIn("rollback was cancelled. No setting changed.", rollback_wrapper)

    def test_real_fresh_run_and_exact_read_only_tool_are_required(self):
        self.assertIn('[Uri]::new($Endpoint, "/v1/runs")', self.script)
        self.assertIn('"/v1/runs/$runId/events"', self.script)
        self.assertIn("windows_list_apps", self.script)
        self.assertIn("CYPHER_RUNTIME_PREFLIGHT_OK", self.script)
        self.assertIn("started_names", self.script)
        self.assertIn("completed_names", self.script)
        self.assertIn("completion_errors", self.script)
        self.assertIn('if ($state -ne "completed")', self.script)

    def test_exact_tool_name_accepts_only_bare_or_canonical_hermes_mcp_name(self):
        helper = self.script.split(
            "function Test-IsExpectedWindowsListAppsToolName", 1
        )[1].split("function Invoke-LocalRuntimePreflight", 1)[0]
        self.assertIn('"windows_list_apps"', self.script)
        self.assertIn('"mcp__hermes_sandbox__windows_list_apps"', self.script)
        self.assertIn("$expectedReadOnlyToolNames", helper)
        self.assertNotIn('EndsWith("windows_list_apps")', helper)
        self.assertNotIn("-match", helper)
        self.assertIn(
            "Test-IsExpectedWindowsListAppsToolName -Name $_", self.script
        )

    def test_preflight_allows_only_discovery_bridge_plus_exact_read_only_tool(self):
        helper = self.script.split(
            "function Test-IsAllowedPreflightToolName", 1
        )[1].split("function Invoke-LocalRuntimePreflight", 1)[0]
        for name in ("tool_search", "tool_describe", "tool_call"):
            self.assertIn(name, self.script)
        self.assertIn("Test-IsExpectedWindowsListAppsToolName", helper)
        self.assertIn("$allowedDiscoveryToolNames", helper)
        self.assertIn("unexpected tool", self.script)

    def test_runs_api_unnamed_sse_frames_read_the_embedded_event_field(self):
        parser = self.script.split("function Get-EventEvidence", 1)[1].split(
            "function Test-IsExpectedWindowsListAppsToolName", 1
        )[0]
        self.assertIn('Properties.Name -contains "event"', parser)
        self.assertIn("[string]$data.event", parser)
        self.assertIn("$embeddedEvent", parser)
        self.assertIn("$eventName + \" \" + $embeddedType + \" \" + $embeddedEvent", parser)

    def test_mcp_probe_is_bounded_and_checks_the_required_tool(self):
        probe = self.script.split("function Invoke-BoundedHermesMcpProbe", 1)[1].split(
            "function Get-EventEvidence", 1
        )[0]
        self.assertIn("WaitForExit($TimeoutSeconds * 1000)", probe)
        self.assertIn("$process.Kill()", probe)
        self.assertIn("mcp test $mcpServerName", probe)
        self.assertIn("windows_list_apps", probe)
        self.assertNotIn("Write-Host $combined", probe)
        self.assertIn(
            "Starting one fresh Hermes run through the bounded discovery bridge",
            self.script,
        )
        self.assertIn("Live preflight still running", self.script)
        self.assertIn("300-second limit", self.script)

    def test_false_continuation_output_is_rejected(self):
        for phrase in (
            "previous response",
            "truncated response",
            "cut off",
            "resume from",
            "continue exactly",
            "what were we working on",
        ):
            self.assertIn(f'"{phrase}"', self.script)

    def test_secrets_and_content_are_not_persisted_or_printed(self):
        self.assertIn("DataProtectionScope]::CurrentUser", self.script)
        self.assertNotIn("Write-Host $apiKey", self.script)
        self.assertNotIn("Out-File", self.script)
        self.assertNotIn("Tee-Object", self.script)
        self.assertNotIn("API_SERVER_KEY=", self.script)
        self.assertNotIn("Write-Host $combined", self.script)

    def test_scope_is_standard_user_loopback_and_non_destructive(self):
        lower = self.script.lower()
        self.assertIn("non-administrator", lower)
        self.assertIn('"127.0.0.1", "localhost", "::1"', self.script)
        self.assertNotIn("runas", lower)
        self.assertNotIn("hermes update", lower)
        self.assertNotIn("ollama rm", lower)
        self.assertNotIn("remove-item -recurse", lower)
        self.assertNotIn("invoke-expression", lower)

    def test_wrappers_are_process_scoped(self):
        for name, action in (
            ("REPAIR_CYPHER_LOCAL_RUNTIME.cmd", "repair"),
            ("TEST_CYPHER_LOCAL_RUNTIME.cmd", "preflight"),
            ("ROLLBACK_CYPHER_LOCAL_RUNTIME.cmd", "rollback"),
        ):
            wrapper = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn("powershell.exe -NoProfile -ExecutionPolicy Bypass -File", wrapper)
            self.assertIn(action, wrapper)


if __name__ == "__main__":
    unittest.main()
