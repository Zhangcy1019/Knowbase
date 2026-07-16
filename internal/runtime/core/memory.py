"""Observation and summary helpers for the runtime loop."""

from __future__ import annotations

from internal.runtime.contracts import (
    RuntimeAgentHints,
    RuntimeExecutionBounds,
    RuntimeMemorySnapshot,
    RuntimeObservation,
    RuntimeProgressSnapshot,
    RuntimeTaskContext,
    RuntimeTurnInput,
)
from internal.runtime.core.state import RuntimeRunState


class RuntimeMemoryManager:
    """Build turn input, summaries, and lightweight run-memory state."""

    def initialize_state(self, *, run, request, state: RuntimeRunState) -> None:
        if not state.facts:
            state.record_fact("objective", request.objective)
            state.record_fact("source_type", request.source_type)
            if request.partition:
                state.record_fact("partition", request.partition)
        if request.task_payload and not state.observations:
            state.add_observation(kind="request_context", payload=request.task_payload)

    def record_tool_result(self, *, state: RuntimeRunState, tool_id: str, output: dict[str, object]) -> None:
        state.add_observation(kind="tool_result", payload={"tool_id": tool_id, "output": output})

    def record_skill_result(self, *, state: RuntimeRunState, skill_id: str, output: dict[str, object]) -> None:
        state.add_observation(kind="skill_result", payload={"skill_id": skill_id, "output": output})

    def record_response(self, *, state: RuntimeRunState, content: str) -> None:
        state.add_observation(kind="response", payload={"content": content})

    def build_memory_snapshot(self, *, state: RuntimeRunState) -> RuntimeMemorySnapshot:
        return RuntimeMemorySnapshot(
            facts=dict(state.facts),
            observations=[
                RuntimeObservation(kind=observation.get("kind", ""), payload=dict(observation.get("payload", {})))
                for observation in state.observations
            ],
        )

    def build_turn_input(
        self,
        *,
        run,
        request,
        state: RuntimeRunState,
    ) -> RuntimeTurnInput:
        return RuntimeTurnInput(
            run_id=run.run_id,
            request_id=request.request_id,
            turn_index=state.turn_count,
            task=RuntimeTaskContext(
                objective=request.objective,
                prompt=request.prompt,
                partition=request.partition,
                source_type=request.source_type,
                source_ref=request.source_ref,
                payload=dict(request.task_payload),
            ),
            memory=self.build_memory_snapshot(state=state),
            bounds=RuntimeExecutionBounds(
                allowed_tools=list(request.allowed_tools),
                allowed_skills=list(request.allowed_skills),
                risk_level=request.risk_level,
                requires_review=request.requires_review,
                remaining_step_budget=max(run.max_steps - run.step_count, 0),
                remaining_tool_budget=max(run.max_tool_calls - run.tool_call_count, 0),
                remaining_skill_budget=max(run.max_skill_calls - run.skill_call_count, 0),
            ),
            progress=RuntimeProgressSnapshot(
                completed_actions=list(state.applied_actions),
                recent_decisions=[
                    item.reasoning_summary or item.decision_id
                    for item in state.decision_history[-3:]
                ],
                recent_failures=[item for item in state.failure_messages[-3:] if item],
                latest_response=state.response_messages[-1] if state.response_messages else "",
            ),
            hints=RuntimeAgentHints(
                actions=[item for item in request.task_hints if isinstance(item, dict)],
                metadata=dict(request.metadata),
            ),
        )

    def build_reasoning_summary(
        self,
        *,
        request,
        state: RuntimeRunState,
    ) -> str:
        return (
            f"Runtime loop processed {state.turn_count} turn(s), "
            f"{len(state.tool_results)} tool call(s), "
            f"{len(state.skill_results)} skill call(s), "
            f"{len(state.observations)} observation(s). "
            f"Objective: {request.objective}"
        )

    def build_final_summary(
        self,
        *,
        request,
        state: RuntimeRunState,
    ) -> str:
        if state.failure_messages:
            return "; ".join(message for message in state.failure_messages if message)
        if state.response_messages:
            return state.response_messages[-1]
        if state.skill_results:
            successful = len([item for item in state.skill_results if item.ok])
            return f"Runtime completed with {successful} successful skill execution(s)."
        if state.tool_results:
            successful = len([item for item in state.tool_results if item.ok])
            return f"Runtime completed with {successful} successful tool execution(s)."
        return request.objective
