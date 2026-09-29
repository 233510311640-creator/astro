from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import uuid


class TaskLifecycleError(RuntimeError):
    """Raised when a task attempts an unsafe or unsupported state transition."""


class TaskPhase(str, Enum):
    UNDERSTAND = "understand"
    PLAN = "plan"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTE = "execute"
    VERIFY = "verify"
    REPORT = "report"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


TERMINAL_PHASES = {
    TaskPhase.COMPLETED,
    TaskPhase.FAILED,
    TaskPhase.CANCELLED,
    TaskPhase.TIMED_OUT,
}


@dataclass(frozen=True)
class TaskEvidence:
    stage: str
    success: bool
    verifier: str
    operation_id: str | None
    observed_at: str


@dataclass
class ReliableTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    phase: TaskPhase = TaskPhase.UNDERSTAND
    action_required: bool = False
    approval_required: bool = False
    plan_fingerprint: str | None = None
    approved_fingerprint: str | None = None
    evidence: list[TaskEvidence] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 1


class ReliableTaskLifecycle:
    """Deterministic task state machine; it stores no prompt or response content."""

    def __init__(self, task: ReliableTask | None = None):
        self.task = task or ReliableTask()

    def _require(self, *phases: TaskPhase) -> None:
        if self.task.phase not in phases:
            expected = ", ".join(phase.value for phase in phases)
            raise TaskLifecycleError(
                f"Task is in {self.task.phase.value}; expected one of: {expected}"
            )

    def plan(
        self,
        *,
        action_required: bool,
        approval_required: bool = False,
        fingerprint: str | None = None,
    ) -> ReliableTask:
        self._require(TaskPhase.UNDERSTAND)
        if approval_required and not action_required:
            raise TaskLifecycleError("Advice-only tasks cannot request execution approval")
        if approval_required and not fingerprint:
            raise TaskLifecycleError("Approval-gated plans require a fingerprint")
        self.task.action_required = action_required
        self.task.approval_required = approval_required
        self.task.plan_fingerprint = fingerprint
        self.task.phase = (
            TaskPhase.WAITING_APPROVAL if approval_required else TaskPhase.PLAN
        )
        return self.task

    def approve(self, fingerprint: str) -> ReliableTask:
        self._require(TaskPhase.WAITING_APPROVAL)
        if fingerprint != self.task.plan_fingerprint:
            raise TaskLifecycleError("Approval fingerprint does not match the current plan")
        self.task.approved_fingerprint = fingerprint
        self.task.phase = TaskPhase.EXECUTE
        return self.task

    def begin_execution(self) -> ReliableTask:
        self._require(TaskPhase.PLAN)
        if not self.task.action_required:
            raise TaskLifecycleError("Advice-only tasks do not have an execution phase")
        if self.task.approval_required:
            raise TaskLifecycleError("This task must be approved before execution")
        self.task.phase = TaskPhase.EXECUTE
        return self.task

    def report_advice(self) -> ReliableTask:
        self._require(TaskPhase.PLAN)
        if self.task.action_required:
            raise TaskLifecycleError("Action tasks require execution evidence")
        self.task.phase = TaskPhase.REPORT
        return self.task

    def record_execution(
        self,
        *,
        success: bool,
        verifier: str,
        operation_id: str | None = None,
    ) -> ReliableTask:
        self._require(TaskPhase.EXECUTE)
        self.task.evidence.append(
            TaskEvidence(
                stage="execute",
                success=success,
                verifier=verifier,
                operation_id=operation_id,
                observed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.task.phase = TaskPhase.VERIFY if success else TaskPhase.FAILED
        return self.task

    def record_verification(
        self,
        *,
        success: bool,
        verifier: str,
        operation_id: str | None = None,
    ) -> ReliableTask:
        self._require(TaskPhase.VERIFY)
        self.task.evidence.append(
            TaskEvidence(
                stage="verify",
                success=success,
                verifier=verifier,
                operation_id=operation_id,
                observed_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        self.task.phase = TaskPhase.REPORT if success else TaskPhase.FAILED
        return self.task

    def complete(self) -> ReliableTask:
        self._require(TaskPhase.REPORT)
        if self.task.action_required:
            executed = any(
                evidence.stage == "execute" and evidence.success
                for evidence in self.task.evidence
            )
            verified = any(
                evidence.stage == "verify" and evidence.success
                for evidence in self.task.evidence
            )
            if not executed or not verified:
                raise TaskLifecycleError(
                    "Action tasks cannot complete without execution and verification evidence"
                )
        self.task.phase = TaskPhase.COMPLETED
        return self.task

    def cancel(self) -> ReliableTask:
        if self.task.phase in TERMINAL_PHASES:
            raise TaskLifecycleError("A terminal task cannot be cancelled again")
        self.task.phase = TaskPhase.CANCELLED
        return self.task

    def time_out(self) -> ReliableTask:
        if self.task.phase in TERMINAL_PHASES:
            raise TaskLifecycleError("A terminal task cannot time out")
        self.task.phase = TaskPhase.TIMED_OUT
        return self.task

    def retry(self) -> ReliableTask:
        self._require(TaskPhase.FAILED, TaskPhase.TIMED_OUT)
        if self.task.retry_count >= self.task.max_retries:
            raise TaskLifecycleError("The bounded retry limit has been reached")
        self.task.retry_count += 1
        self.task.phase = TaskPhase.PLAN
        return self.task
