"""Working memory and observation helpers for the runtime loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from internal.runtime.contracts import RuntimeMemorySnapshot, RuntimeObservation, RuntimeTurnInput
from internal.runtime.session import RuntimeLoopState, RuntimeSession


@dataclass(slots=True)
class RuntimeWorkingMemory:
    """Mutable working memory carried across one runtime loop."""

    observations: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)

    def add_observation(self, *, kind: str, payload: dict[str, Any]) -> None:
        self.observations.append({"kind": kind, "payload": payload})

    def record_fact(self, key: str, value: Any) -> None:
        if key.strip():
            self.facts[key] = value


class RuntimeMemoryManager:
    """Build summaries and maintain working memory for one run."""

    def build_initial_memory(self, *, session: RuntimeSession) -> RuntimeWorkingMemory:
        memory = RuntimeWorkingMemory()
        memory.record_fact("objective", session.request.objective)
        memory.record_fact("source_type", session.request.source_type)
        if session.request.partition:
            memory.record_fact("partition", session.request.partition)
        if session.request.context:
            memory.add_observation(kind="request_context", payload=session.request.context)
        return memory

    def record_tool_result(self, *, memory: RuntimeWorkingMemory, tool_id: str, output: dict[str, Any]) -> None:
        memory.add_observation(kind="tool_result", payload={"tool_id": tool_id, "output": output})

    def record_skill_result(self, *, memory: RuntimeWorkingMemory, skill_id: str, output: dict[str, Any]) -> None:
        memory.add_observation(kind="skill_result", payload={"skill_id": skill_id, "output": output})

    def record_response(self, *, memory: RuntimeWorkingMemory, content: str) -> None:
        memory.add_observation(kind="response", payload={"content": content})

    def build_memory_snapshot(self, *, memory: RuntimeWorkingMemory) -> RuntimeMemorySnapshot:
        return RuntimeMemorySnapshot(
            facts=dict(memory.facts),
            observations=[
                RuntimeObservation(kind=observation.get("kind", ""), payload=dict(observation.get("payload", {})))
                for observation in memory.observations
            ],
        )

    def build_turn_input(
        self,
        *,
        session: RuntimeSession,
        loop_state: RuntimeLoopState,
        memory: RuntimeWorkingMemory,
    ) -> RuntimeTurnInput:
        run = session.run
        request = session.request
        return RuntimeTurnInput(
            run_id=run.run_id,
            request_id=request.request_id,
            turn_index=loop_state.turn_count,
            objective=request.objective,
            prompt=request.prompt,
            partition=request.partition,
            source_type=request.source_type,
            source_ref=request.source_ref,
            context=request.context,
            memory=self.build_memory_snapshot(memory=memory),
            prior_decisions=list(loop_state.decision_history),
            allowed_tools=list(request.allowed_tools),
            allowed_skills=list(request.allowed_skills),
            risk_level=request.risk_level,
            requires_review=request.requires_review,
            remaining_step_budget=max(run.max_steps - run.step_count, 0),
            remaining_tool_budget=max(run.max_tool_calls - run.tool_call_count, 0),
            remaining_skill_budget=max(run.max_skill_calls - run.skill_call_count, 0),
            failure_messages=list(loop_state.failure_messages),
            response_messages=list(loop_state.response_messages),
            metadata=dict(request.metadata),
        )

    def build_reasoning_summary(
        self,
        *,
        session: RuntimeSession,
        loop_state: RuntimeLoopState,
        memory: RuntimeWorkingMemory,
    ) -> str:
        return (
            f"Runtime loop processed {loop_state.turn_count} turn(s), "
            f"{len(loop_state.tool_results)} tool call(s), "
            f"{len(loop_state.skill_results)} skill call(s), "
            f"{len(memory.observations)} observation(s). "
            f"Objective: {session.request.objective}"
        )

    def build_final_summary(
        self,
        *,
        session: RuntimeSession,
        loop_state: RuntimeLoopState,
    ) -> str:
        if loop_state.failure_messages:
            return "; ".join(message for message in loop_state.failure_messages if message)
        if loop_state.response_messages:
            return loop_state.response_messages[-1]
        if loop_state.skill_results:
            successful = len([item for item in loop_state.skill_results if item.ok])
            return f"Runtime completed with {successful} successful skill execution(s)."
        if loop_state.tool_results:
            successful = len([item for item in loop_state.tool_results if item.ok])
            return f"Runtime completed with {successful} successful tool execution(s)."
        return session.request.objective
