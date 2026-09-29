from __future__ import annotations

import unittest

from local_assistant.task_lifecycle import (
    ReliableTaskLifecycle,
    TaskLifecycleError,
    TaskPhase,
)


class ReliableTaskLifecycleTests(unittest.TestCase):
    def test_action_cannot_claim_completion_without_verified_evidence(self):
        lifecycle = ReliableTaskLifecycle()
        lifecycle.plan(action_required=True)
        lifecycle.begin_execution()
        lifecycle.record_execution(success=True, verifier="capability_broker", operation_id="op-1")
        self.assertEqual(lifecycle.task.phase, TaskPhase.VERIFY)
        with self.assertRaises(TaskLifecycleError):
            lifecycle.complete()
        lifecycle.record_verification(success=True, verifier="postcondition", operation_id="op-1")
        lifecycle.complete()
        self.assertEqual(lifecycle.task.phase, TaskPhase.COMPLETED)

    def test_approval_is_bound_to_the_current_fingerprint(self):
        lifecycle = ReliableTaskLifecycle()
        lifecycle.plan(
            action_required=True,
            approval_required=True,
            fingerprint="exact-plan",
        )
        with self.assertRaises(TaskLifecycleError):
            lifecycle.approve("different-plan")
        lifecycle.approve("exact-plan")
        self.assertEqual(lifecycle.task.phase, TaskPhase.EXECUTE)

    def test_advice_task_skips_execution_but_still_reports(self):
        lifecycle = ReliableTaskLifecycle()
        lifecycle.plan(action_required=False)
        lifecycle.report_advice()
        lifecycle.complete()
        self.assertEqual(lifecycle.task.phase, TaskPhase.COMPLETED)
        self.assertEqual(lifecycle.task.evidence, [])

    def test_failed_execution_cannot_be_reported_as_done(self):
        lifecycle = ReliableTaskLifecycle()
        lifecycle.plan(action_required=True)
        lifecycle.begin_execution()
        lifecycle.record_execution(success=False, verifier="capability_broker")
        self.assertEqual(lifecycle.task.phase, TaskPhase.FAILED)
        with self.assertRaises(TaskLifecycleError):
            lifecycle.complete()

    def test_retry_is_bounded(self):
        lifecycle = ReliableTaskLifecycle()
        lifecycle.plan(action_required=True)
        lifecycle.begin_execution()
        lifecycle.record_execution(success=False, verifier="capability_broker")
        lifecycle.retry()
        lifecycle.begin_execution()
        lifecycle.record_execution(success=False, verifier="capability_broker")
        with self.assertRaises(TaskLifecycleError):
            lifecycle.retry()


if __name__ == "__main__":
    unittest.main()
