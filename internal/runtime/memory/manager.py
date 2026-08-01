"""Observation and summary helpers for the runtime loop."""

from __future__ import annotations

from pathlib import Path

from internal.runtime.contracts import (
    RuntimeAgentHints,
    RuntimeExecutionBounds,
    RuntimeMemorySnapshot,
    RuntimeObservation,
    RuntimeProgressSnapshot,
    RuntimeTaskContext,
    RuntimeTurnInput,
)
from internal.runtime.memory.state import RuntimeRunState


class RuntimeMemoryManager:
    """Build turn input, summaries, and lightweight run-memory state."""

    def __init__(self, *, capability_executor=None) -> None:
        self._capability_executor = capability_executor

    def initialize_state(self, *, run, request, state: RuntimeRunState) -> None:
        work_profile = request.work
        if not state.facts:
            state.record_fact("objective", work_profile.objective)
            state.record_fact("source_type", request.source_type)
            if request.partition:
                state.record_fact("partition", request.partition)
            source_text = str(work_profile.input_context.get("source_text") or "").strip() or self._read_source_text_from_request(request=request)
            if source_text:
                state.record_fact("source_text", source_text)
        if work_profile.input_context and not state.observations:
            state.add_observation(kind="request_context", payload=work_profile.input_context)

    def record_tool_result(self, *, state: RuntimeRunState, tool_id: str, output: dict[str, object]) -> None:
        state.add_observation(kind="tool_result", payload={"tool_id": tool_id, "output": output})

    def record_skill_result(self, *, state: RuntimeRunState, skill_id: str, output: dict[str, object]) -> None:
        state.add_observation(kind="skill_result", payload={"skill_id": skill_id, "output": output})

    def record_response(self, *, state: RuntimeRunState, content: str) -> None:
        state.add_observation(kind="response", payload={"content": content})

    def build_memory_snapshot(self, *, state: RuntimeRunState) -> RuntimeMemorySnapshot:
        return RuntimeMemorySnapshot(
            facts=dict(state.facts),
            observations=[RuntimeObservation(kind=item.get("kind", ""), payload=dict(item.get("payload", {}))) for item in state.observations],
        )

    def build_turn_input(self, *, run, request, state: RuntimeRunState) -> RuntimeTurnInput:
        work_profile = request.work
        verification_profile = request.resolved_verification_profile()
        verification_tools = list(verification_profile.allowed_tools)
        verification_skills = list(verification_profile.allowed_skills)
        current_run = run
        available_tool_specs = []
        available_skill_specs = []
        if self._capability_executor is not None:
            current_run = self._capability_executor.current_run(run)
            available_tool_specs = [spec for tool_id in work_profile.allowed_tools if (spec := self._capability_executor.resolve_tool_spec(tool_id)) is not None]
            available_skill_specs = [spec for skill_id in work_profile.allowed_skills if (spec := self._capability_executor.resolve_skill_spec(skill_id)) is not None]
            available_verification_tool_specs = [spec for tool_id in verification_tools if (spec := self._capability_executor.resolve_tool_spec(tool_id)) is not None]
            available_verification_skill_specs = [spec for skill_id in verification_skills if (spec := self._capability_executor.resolve_skill_spec(skill_id)) is not None]
        else:
            available_verification_tool_specs = []
            available_verification_skill_specs = []
        return RuntimeTurnInput(
            run_id=run.run_id,
            request_id=request.request_id,
            turn_index=state.turn_count,
            task=RuntimeTaskContext(
                objective=work_profile.objective,
                mission_summary=work_profile.mission_summary,
                instructions=list(work_profile.instructions),
                partition=request.partition,
                source_type=request.source_type,
                source_ref=request.source_ref,
                work=work_profile.model_copy(),
                input_context=dict(work_profile.input_context),
                output_contract=dict(work_profile.output_contract),
                acceptance=request.acceptance.model_copy(),
                verification=verification_profile,
                stop_policy=request.stop_policy.model_copy(),
                risk_policy=request.risk_policy.model_copy(),
                verification_skills=list(verification_skills),
                verification_tools=list(verification_tools),
            ),
            memory=self.build_memory_snapshot(state=state),
            bounds=RuntimeExecutionBounds(
                allowed_tools=list(work_profile.allowed_tools),
                allowed_skills=list(work_profile.allowed_skills),
                allowed_verification_tools=list(verification_tools),
                allowed_verification_skills=list(verification_skills),
                available_tool_specs=available_tool_specs,
                available_skill_specs=available_skill_specs,
                available_verification_tool_specs=available_verification_tool_specs,
                available_verification_skill_specs=available_verification_skill_specs,
                risk_level=request.risk_level,
                requires_review=request.requires_review,
                remaining_step_budget=max(current_run.max_steps - current_run.step_count, 0),
                remaining_tool_budget=max(current_run.max_tool_calls - current_run.tool_call_count, 0),
                remaining_skill_budget=max(current_run.max_skill_calls - current_run.skill_call_count, 0),
            ),
            progress=RuntimeProgressSnapshot(
                completed_actions=list(state.applied_actions),
                recent_decisions=[item.reasoning_summary or item.decision_id for item in state.decision_history[-3:]],
                recent_failures=[item for item in state.failure_messages[-3:] if item],
                latest_response=state.response_messages[-1] if state.response_messages else "",
            ),
            hints=RuntimeAgentHints(actions=list(work_profile.capability_hints), metadata=dict(request.metadata)),
        )

    def build_reasoning_summary(self, *, request, state: RuntimeRunState) -> str:
        return (
            f"Runtime loop processed {state.turn_count} turn(s), "
            f"{len(state.tool_results)} tool call(s), "
            f"{len(state.skill_results)} skill call(s), "
            f"{len(state.observations)} observation(s). "
            f"Objective: {request.work.objective}"
        )

    def build_final_summary(self, *, request, state: RuntimeRunState) -> str:
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
        return request.work.objective

    @staticmethod
    def _read_source_text_from_request(*, request) -> str:
        file_path = str(request.work.input_context.get("file_path") or "").strip()
        if not file_path:
            return ""
        try:
            path = Path(file_path).expanduser()
            if not path.exists() or not path.is_file():
                return ""
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
