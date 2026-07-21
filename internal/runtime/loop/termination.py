"""Runtime loop termination policy."""

from __future__ import annotations

from dataclasses import dataclass

from internal.runtime.contracts import RuntimeExecutionStatus
from internal.runtime.memory.state import RuntimeRunState


@dataclass(slots=True)
class RuntimeTerminationDecision:
    """Normalized loop termination outcome."""

    should_stop: bool = False
    status: RuntimeExecutionStatus = "completed"
    requires_review: bool = False
    reason: str = ""


class RuntimeTerminationPolicy:
    """Determine whether a runtime loop should stop after a decision or action execution."""

    def __init__(self, *, acceptance_verifier=None):
        self._acceptance_verifier = acceptance_verifier

    def should_stop(self, *, run, request, state, decision) -> RuntimeTerminationDecision:
        del run
        if state.failure_messages:
            return RuntimeTerminationDecision(
                should_stop=True,
                status="failed",
                requires_review=True,
                reason=state.failure_messages[-1],
            )
        if self._acceptance_satisfied(request=request, state=state):
            return RuntimeTerminationDecision(
                should_stop=True,
                status="completed",
                requires_review=False,
                reason="acceptance satisfied",
            )
        if decision.requires_review:
            return RuntimeTerminationDecision(
                should_stop=True,
                status="requires_review",
                requires_review=True,
                reason=decision.reasoning_summary or "planner requested review",
            )
        if decision.should_stop:
            return RuntimeTerminationDecision(
                should_stop=True,
                status="completed",
                requires_review=False,
                reason=decision.reasoning_summary or "planner requested stop",
            )
        return RuntimeTerminationDecision()

    def _acceptance_satisfied(self, *, request, state: RuntimeRunState) -> bool:
        if self._acceptance_verifier is None:
            return False
        stop_when_acceptance_satisfied = bool(
            getattr(getattr(request, "stop_policy", None), "stop_when_acceptance_satisfied", False)
        )
        if not stop_when_acceptance_satisfied:
            return False
        completion_checks = list(getattr(getattr(request, "acceptance", None), "completion_checks", []) or [])
        if not completion_checks:
            return False
        return bool(self._acceptance_verifier.is_satisfied(request=request, state=state))
