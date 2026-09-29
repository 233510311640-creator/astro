from pathlib import Path
import unittest
from xml.etree import ElementTree


ROOT = Path(__file__).parents[1]


class ResidentHostWindowsScriptTests(unittest.TestCase):
    def setUp(self):
        self.resident = (
            ROOT / "scripts" / "resident_assistant_windows.ps1"
        ).read_text(encoding="utf-8")
        self.installer = (
            ROOT / "scripts" / "install_resident_host_windows.ps1"
        ).read_text(encoding="utf-8")
        self.manager = (
            ROOT / "scripts" / "manage_resident_host_windows.ps1"
        ).read_text(encoding="utf-8")

    def test_resident_uses_authenticated_loopback_responses_api(self):
        self.assertIn('"127.0.0.1", "localhost", "::1"', self.resident)
        self.assertIn('AuthenticationHeaderValue("Bearer", $apiKey)', self.resident)
        self.assertIn('"/v1/responses"', self.resident)
        self.assertIn('conversation = $script:conversation', self.resident)
        self.assertNotIn("API_SERVER_KEY=", self.resident)

    def test_resident_has_single_instance_tray_and_global_hotkey(self):
        self.assertIn("LocalAssistantHostResidentV061", self.resident)
        self.assertIn("System.Windows.Forms.NotifyIcon", self.resident)
        self.assertIn("RegisterHotKey", self.resident)
        self.assertIn("ModControl | ModAlt | ModNoRepeat", self.resident)
        self.assertIn("VkSpace", self.resident)

    def test_native_cypher_overlay_replaces_temporary_dialogs_safely(self):
        self.assertIn("PresentationFramework", self.resident)
        self.assertIn("WindowsFormsIntegration", self.resident)
        self.assertIn('WindowStyle="None"', self.resident)
        self.assertIn('AllowsTransparency="True"', self.resident)
        self.assertIn("EnableModelessKeyboardInterop", self.resident)
        self.assertIn("LOCAL / PRIVATE / APPROVALS ENFORCED", self.resident)
        self.assertIn("Set-CypherResponseText", self.resident)
        self.assertNotIn("function Show-CommandDialog", self.resident)
        self.assertNotIn("function Show-ResponseWindow", self.resident)
        self.assertNotIn("WebView2", self.resident)
        xaml = self.resident.split("$xaml = @'", 1)[1].split("'@", 1)[0]
        ElementTree.fromstring(xaml)
        stop_call = self.installer.index("\nStop-ExistingResidentHost\n")
        self.assertLess(stop_call, self.installer.index("Copy-Item -LiteralPath $residentSource"))

    def test_resident_does_not_log_prompt_or_response_content(self):
        logging_function = self.resident.split("function Write-HostEvent", 1)[1].split(
            "function Get-PlaintextSecret", 1
        )[0]
        self.assertNotIn("commandText", logging_function)
        self.assertNotIn("ResponseObject", logging_function)
        self.assertIn("event = $Event", logging_function)
        self.assertIn("duration_ms = $DurationMs", logging_function)

    def test_installer_uses_dpapi_and_managed_loopback_api_block(self):
        self.assertIn("ConvertFrom-SecureString", self.installer)
        self.assertIn("API_SERVER_ENABLED=true", self.installer)
        self.assertIn("API_SERVER_HOST=127.0.0.1", self.installer)
        self.assertIn("API_SERVER_PORT=8642", self.installer)
        self.assertIn("BEGIN LOCAL_ASSISTANT_HOST_V0_6", self.installer)
        self.assertIn("RandomNumberGenerator", self.installer)
        self.assertNotIn("API_SERVER_CORS_ORIGINS", self.installer)

    def test_resident_host_does_not_self_elevate(self):
        lower = self.installer.lower()
        self.assertIn('getfolderpath("startup")', lower)
        self.assertIn("gateway install", lower)
        self.assertIn("-windowstyle hidden", lower)
        self.assertNotIn("runas", lower)
        self.assertNotIn("highest", lower)
        self.assertNotIn("--yolo", lower)

    def test_first_gateway_install_waits_instead_of_immediately_restarting(self):
        self.assertIn("function Test-HermesGatewayInstalled", self.installer)
        self.assertIn("$gatewayWasInstalled = Test-HermesGatewayInstalled", self.installer)
        self.assertIn("if ($gatewayWasInstalled)", self.installer)
        self.assertIn("Wait-HermesApi -TimeoutSeconds 120", self.installer)
        gateway_block = self.installer.split("if ($gatewayWasInstalled)", 1)[1]
        install_branch = gateway_block.split("} else {", 1)[1].split(
            "if (-not (Wait-HermesApi", 1
        )[0]
        self.assertIn("gateway install", install_branch)
        self.assertNotIn("gateway restart", install_branch)

    def test_installer_runs_only_current_required_test_suites(self):
        self.assertIn("$installTestPatterns", self.installer)
        self.assertIn('"test_resident_host_windows_scripts.py"', self.installer)
        self.assertIn('"test_organization_planner.py"', self.installer)
        self.assertNotIn('"test_policy_and_plans.py"', self.installer)

    def test_manager_stop_is_cooperative_and_uninstall_is_exact(self):
        self.assertIn("stop.request", self.manager)
        self.assertIn("REMOVE RESIDENT HOST", self.manager)
        self.assertIn("Refusing to remove an unexpected install path", self.manager)
        self.assertNotIn("Stop-Process", self.manager)
        self.assertNotIn("taskkill", self.manager.lower())

    def test_voice_is_explicitly_disabled_in_this_milestone(self):
        self.assertIn("microphone_enabled = $false", self.installer)
        self.assertIn("Microphone: disabled", self.resident)
        self.assertNotIn("SpeechRecognition", self.resident)


if __name__ == "__main__":
    unittest.main()
