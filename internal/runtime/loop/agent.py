"""Runtime loop agent implementations."""

from __future__ import annotations

from typing import Protocol

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeDecision, RuntimeRunRequest, RuntimeTurnInput
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.loop.turn_planner import RuntimeTurnPlannerPort


class RuntimeAgentPort(Protocol):
    """Agent interface used by the runtime orchestrator."""

    def decide(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeDecision:
        ...


class RuntimeLoopAgent:
    """Default runtime agent that delegates one turn to an injected planner."""

    def __init__(self, *, planner: RuntimeTurnPlannerPort):
        self._planner = planner

    def decide(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeDecision:
        return self._planner.plan_turn(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
        )
