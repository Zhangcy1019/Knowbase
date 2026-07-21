"""Planning contracts for runtime loop agents."""

from __future__ import annotations

from typing import Protocol

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeDecision, RuntimeRunRequest, RuntimeTurnInput
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.llm.decisioning import (
    DefaultRuntimeDecisionGenerator,
    RuntimeDecisionGeneratorPort,
)
from internal.runtime.loop.planner_components import (
    DefaultRuntimeObservationAssembler,
    DefaultRuntimeStopEvaluator,
    RuntimeObservationAssemblerPort,
    RuntimeStopEvaluatorPort,
)


class RuntimeTurnPlannerPort(Protocol):
    """Produce one runtime decision for the current turn."""

    def plan_turn(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeDecision:
        ...


class UnconfiguredRuntimeTurnPlanner:
    """Placeholder turn planner used until a real planner is wired in."""

    def plan_turn(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeDecision:
        raise NotImplementedError(
            "Runtime turn planner is not configured. Inject a concrete RuntimeTurnPlannerPort "
            "implementation that can consume RuntimeTurnInput and produce RuntimeDecision."
        )


class RuntimeTurnPlanner:
    """Default planner pipeline for one runtime turn."""

    def __init__(
        self,
        *,
        observation_assembler: RuntimeObservationAssemblerPort | None = None,
        stop_evaluator: RuntimeStopEvaluatorPort | None = None,
        decision_generator: RuntimeDecisionGeneratorPort | None = None,
    ):
        self._observation_assembler = observation_assembler or DefaultRuntimeObservationAssembler()
        self._stop_evaluator = stop_evaluator or DefaultRuntimeStopEvaluator()
        self._decision_generator = decision_generator or DefaultRuntimeDecisionGenerator()

    def plan_turn(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimeDecision:
        planner_context = self._observation_assembler.assemble(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
        )
        stop_assessment = self._stop_evaluator.assess(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
            planner_context=planner_context,
        )
        return self._decision_generator.generate(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
            planner_context=planner_context,
            stop_assessment=stop_assessment,
        )
