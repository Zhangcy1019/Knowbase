"""Termination decisions for the runtime loop."""

from __future__ import annotations

from dataclasses import dataclass

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeDecision, RuntimeExecutionStatus, RuntimeRunRequest
from internal.runtime.core.state import RuntimeRunState


@dataclass(slots=True)
class RuntimeTerminationDecision:
    should_stop: bool = False
    status: RuntimeExecutionStatus = "completed"
    reason: str = ""
    requires_review: bool = False


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
            return RuntimeTerminationDecision(
                should_stop=True,
                status="completed",
                reason="planner requested review",
                requires_review=True,
            )
        if decision is not None and decision.should_stop:
            return RuntimeTerminationDecision(
                should_stop=True,
                status="completed",
                reason="planner requested stop",
                requires_review=request.requires_review,
            )
        return RuntimeTerminationDecision()
