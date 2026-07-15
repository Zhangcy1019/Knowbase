"""Composable planner components for one runtime turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from internal.models import AgentRun
from internal.runtime.contracts import RuntimeRunRequest, RuntimeTurnInput
from internal.runtime.core.state import RuntimeRunState


@dataclass(slots=True)
class RuntimePlannerObservation:
    """Normalized observation package prepared from the current turn input."""

    objective: str = ""
    partition: str = ""
    facts: dict[str, object] = field(default_factory=dict)
    observations: list[dict[str, object]] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    recent_failures: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RuntimePlannerContext:
    """Decision-generator-facing context derived from one runtime turn."""

    run_id: str = ""
    request_id: str = ""
    turn_index: int = 0
    objective: str = ""
    prompt: str = ""
    partition: str = ""
    source_type: str = ""
    source_ref: str = ""
    task_payload: dict[str, object] = field(default_factory=dict)
    facts: dict[str, object] = field(default_factory=dict)
    observations: list[dict[str, object]] = field(default_factory=list)
    completed_actions: list[str] = field(default_factory=list)
    recent_decisions: list[str] = field(default_factory=list)
    recent_failures: list[str] = field(default_factory=list)
    latest_response: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    allowed_skills: list[str] = field(default_factory=list)
    risk_level: str = "medium"
    requires_review: bool = False
    remaining_step_budget: int = 0
    remaining_tool_budget: int = 0
    remaining_skill_budget: int = 0
    hinted_actions: list[dict[str, object]] = field(default_factory=list)
    hint_metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimePlannerStopAssessment:
    """Planner-side stop assessment before action proposal."""

    should_stop: bool = False
    reason: str = ""
    requires_review: bool = False


class RuntimeObservationAssemblerPort(Protocol):
    def assemble(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimePlannerContext:
        ...


class RuntimeStopEvaluatorPort(Protocol):
    def assess(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
        planner_context: RuntimePlannerContext,
    ) -> RuntimePlannerStopAssessment:
        ...


class DefaultRuntimeObservationAssembler:
    """Build a compact planner context from the current turn input."""

    def assemble(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
    ) -> RuntimePlannerContext:
        observation = RuntimePlannerObservation(
            objective=turn_input.task.objective,
            partition=turn_input.task.partition,
            facts=dict(turn_input.memory.facts),
            observations=[item.model_dump(mode="json") for item in turn_input.memory.observations],
            completed_actions=list(turn_input.progress.completed_actions),
            recent_failures=list(turn_input.progress.recent_failures),
        )
        return RuntimePlannerContext(
            run_id=turn_input.run_id,
            request_id=turn_input.request_id,
            turn_index=turn_input.turn_index,
            objective=turn_input.task.objective,
            prompt=turn_input.task.prompt,
            partition=turn_input.task.partition,
            source_type=turn_input.task.source_type,
            source_ref=turn_input.task.source_ref,
            task_payload=dict(turn_input.task.payload),
            facts=dict(observation.facts),
            observations=list(observation.observations),
            completed_actions=list(observation.completed_actions),
            recent_decisions=list(turn_input.progress.recent_decisions),
            recent_failures=list(observation.recent_failures),
            latest_response=turn_input.progress.latest_response,
            allowed_tools=list(turn_input.bounds.allowed_tools),
            allowed_skills=list(turn_input.bounds.allowed_skills),
            risk_level=turn_input.bounds.risk_level,
            requires_review=turn_input.bounds.requires_review,
            remaining_step_budget=turn_input.bounds.remaining_step_budget,
            remaining_tool_budget=turn_input.bounds.remaining_tool_budget,
            remaining_skill_budget=turn_input.bounds.remaining_skill_budget,
            hinted_actions=[dict(item) for item in turn_input.hints.actions],
            hint_metadata=dict(turn_input.hints.metadata),
        )


class DefaultRuntimeStopEvaluator:
    def assess(
        self,
        *,
        run: AgentRun,
        request: RuntimeRunRequest,
        state: RuntimeRunState,
        turn_input: RuntimeTurnInput,
        planner_context: RuntimePlannerContext,
    ) -> RuntimePlannerStopAssessment:
        if planner_context.remaining_step_budget <= 0:
            return RuntimePlannerStopAssessment(should_stop=True, reason="step_budget_exhausted")
        if planner_context.remaining_tool_budget <= 0 and planner_context.remaining_skill_budget <= 0:
            return RuntimePlannerStopAssessment(should_stop=True, reason="action_budget_exhausted")
        return RuntimePlannerStopAssessment()


__all__ = [
    "RuntimePlannerObservation",
    "RuntimePlannerContext",
    "RuntimePlannerStopAssessment",
    "RuntimeObservationAssemblerPort",
    "RuntimeStopEvaluatorPort",
    "DefaultRuntimeObservationAssembler",
    "DefaultRuntimeStopEvaluator",
]
