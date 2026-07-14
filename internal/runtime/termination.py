"""Termination decisions for the runtime loop."""

from __future__ import annotations

from dataclasses import dataclass

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeDecision, RuntimeExecutionStatus, RuntimeRunRequest
from internal.runtime.state import RuntimeRunState


@dataclass(slots=True)
class RuntimeTerminationDecision:
    should_stop: bool = False
    status: RuntimeExecutionStatus = "completed"
    reason: str = ""


class RuntimeTerminationPolicy:
    """Decide when one runtime loop should stop and what final status to report."""

    def should_stop(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        decision: RuntimeDecision | None = None,
    ) -> RuntimeTerminationDecision:
        if state.failure_messages:
            return RuntimeTerminationDecision(should_stop=True, status="failed", reason=state.failure_messages[-1])
        if decision is not None and decision.requires_review:
            return RuntimeTerminationDecision(should_stop=True, status="requires_review", reason="planner requested review")
        if decision is not None and decision.should_stop:
            status: RuntimeExecutionStatus = "requires_review" if request.requires_review else "completed"
            return RuntimeTerminationDecision(should_stop=True, status=status, reason="planner requested stop")
        return RuntimeTerminationDecision()
