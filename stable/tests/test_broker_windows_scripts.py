from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class BrokerWindowsScriptTests(unittest.TestCase):
    def test_launcher_uses_python_312_and_module_mode(self):
        source = (ROOT / "scripts" / "start_capability_broker_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("py -3.12 -m local_assistant.broker_mcp", source)
        self.assertIn("$env:PYTHONPATH", source)
        self.assertIn("LocalApplicationData", source)
        self.assertIn("--audit $auditPath", source)
        self.assertIn("--state $statePath", source)
        self.assertIn("--inventory-config $inventoryConfigPath", source)
        self.assertIn("--organization-destinations $organizationDestinationPath", source)
        self.assertIn("--organization-state $organizationStatePath", source)
        self.assertIn("--operator-permissions $operatorPermissionsPath", source)
        self.assertIn("--operator-state $operatorStatePath", source)
        self.assertIn("--operator-quarantine $operatorQuarantinePath", source)
        self.assertIn("--windows-apps $windowsAppsPath", source)

    def test_setup_does_not_execute_hermes_commands(self):
        source = (ROOT / "scripts" / "setup_capability_broker_windows.ps1").read_text(
            encoding="utf-8"
        ).lower()
        executable_lines = [
            line.strip()
            for line in source.splitlines()
            if not line.strip().startswith("hermes mcp add")
        ]
        self.assertNotIn("& hermes", "\n".join(executable_lines))
        self.assertIn("register_command.txt", source)
        self.assertIn("unittest discover", source)
        self.assertIn("local_assistant.operator_preflight", source)
        self.assertIn("windows dpapi preflight failed", source)
        self.assertIn("local_assistant.windows_admin", source)
        self.assertIn("seed-builtins", source)

    def test_windows_app_manager_is_human_side_only(self):
        source = (ROOT / "scripts" / "manage_windows_apps_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_assistant.windows_admin", source)
        self.assertNotIn("local_assistant.broker_mcp", source)
        self.assertIn(
            'ValidateSet("list", "seed-builtins", "add", "remove", "set-text-entry", "set-app-user-model-id")',
            source,
        )

    def test_combined_windows_operator_installer_runs_broker_before_core(self):
        source = (
            ROOT / "scripts" / "install_cypher_windows_operator_preview_windows.ps1"
        ).read_text(encoding="utf-8")
        broker_at = source.index("setup_capability_broker_windows.ps1")
        core_at = source.index("install_cypher_core_preview_windows.ps1")
        self.assertLess(broker_at, core_at)
        self.assertIn("REGISTER_COMMAND.txt", source)
        self.assertNotIn("hermes mcp remove", source.lower())
        self.assertNotIn("hermes mcp add", source.lower())

    def test_human_approval_script_invokes_admin_module_not_mcp(self):
        source = (ROOT / "scripts" / "manage_capability_broker_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_assistant.broker_admin", source)
        self.assertNotIn("local_assistant.broker_mcp", source)
        self.assertIn('ValidateSet("list", "show", "approve", "undo")', source)

    def test_inventory_allowlist_script_is_human_side_only(self):
        source = (ROOT / "scripts" / "manage_inventory_roots_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_assistant.inventory_admin", source)
        self.assertNotIn("local_assistant.broker_mcp", source)
        self.assertIn('ValidateSet("list", "add", "remove")', source)

    def test_organization_review_script_is_human_side_only(self):
        source = (ROOT / "scripts" / "manage_organization_plans_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_assistant.organization_admin", source)
        self.assertNotIn("local_assistant.broker_mcp", source)
        self.assertIn('"add-destination"', source)
        self.assertIn('"review"', source)
        self.assertIn('"reject"', source)

    def test_permissioned_operator_manager_is_human_side_only(self):
        source = (ROOT / "scripts" / "manage_permissioned_operator_windows.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("local_assistant.operator_admin", source)
        self.assertNotIn("local_assistant.broker_mcp", source)
        self.assertIn("CommandArguments", source)


if __name__ == "__main__":
    unittest.main()
