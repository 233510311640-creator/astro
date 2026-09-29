"""Lifecycle checks for the supervised, no-action microphone runner."""

import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import call, patch


SCRIPT = Path(__file__).parents[1] / "scripts" / "run_wake_acceptance_windows.py"
spec = importlib.util.spec_from_file_location("run_wake_acceptance_windows", SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class WakeAcceptanceRunnerTests(TestCase):
    def test_running_host_is_restored_even_when_test_fails(self):
        with patch.object(runner, "manager_status", side_effect=["ready", "stopped", "stopped"]), \
             patch.object(runner, "host_process_count", side_effect=[0, 0]), \
             patch.object(runner, "manager_action") as manage, \
             patch.object(runner, "wait_until_ready") as ready:
            self.assertEqual(1, runner.managed_test(lambda: 1))
        self.assertEqual([call("stop"), call("start")], manage.call_args_list)
        ready.assert_called_once()

    def test_already_stopped_host_is_not_started(self):
        with patch.object(runner, "manager_status", side_effect=["stopped", "stopped"]), \
             patch.object(runner, "host_process_count", return_value=0), \
             patch.object(runner, "manager_action") as manage:
            self.assertEqual(0, runner.managed_test(lambda: 0))
        manage.assert_not_called()

    def test_working_host_is_never_stopped(self):
        with patch.object(runner, "manager_status", return_value="working"), \
             patch.object(runner, "manager_action") as manage:
            with self.assertRaises(runner.AcceptanceSetupError):
                runner.managed_test(lambda: 0)
        manage.assert_not_called()

    def test_process_still_running_prevents_test_and_duplicate_restart(self):
        ran = False

        def test():
            nonlocal ran
            ran = True
            return 0

        with patch.object(runner, "manager_status", side_effect=["ready", "stopped", "ready"]), \
             patch.object(runner, "host_process_count", side_effect=[1, 1]), \
             patch.object(runner, "manager_action") as manage:
            with self.assertRaises(runner.AcceptanceSetupError):
                runner.managed_test(test)
        self.assertFalse(ran)
        self.assertEqual([call("stop")], manage.call_args_list)

    def test_test_exception_still_restores_host(self):
        def failed_test():
            raise RuntimeError("test failure")

        with patch.object(runner, "manager_status", side_effect=["ready", "stopped", "stopped"]), \
             patch.object(runner, "host_process_count", side_effect=[0, 0]), \
             patch.object(runner, "manager_action") as manage, \
             patch.object(runner, "wait_until_ready"):
            with self.assertRaises(RuntimeError):
                runner.managed_test(failed_test)
        self.assertEqual([call("stop"), call("start")], manage.call_args_list)
