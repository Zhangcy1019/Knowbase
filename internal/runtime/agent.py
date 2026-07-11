"""Runtime agent protocol and deterministic implementation."""

from __future__ import annotations

from typing import Protocol

from internal.runtime.context import RuntimeAgentContext
from internal.runtime.contracts import RuntimeAction, RuntimeDecision


class RuntimeAgentPort(Protocol):
    """Agent interface used by the runtime orchestrator."""

    def decide(self, *, context: RuntimeAgentContext) -> RuntimeDecision:
        ...


class DeterministicRuntimeAgent:
    """Deterministically emit one first-turn decision from request constraints."""

    def decide(self, *, context: RuntimeAgentContext) -> RuntimeDecision:
        session = context.session
        turn_input = context.turn_input
        loop_state = context.loop_state
        if loop_state.turn_count > 0:
            return RuntimeDecision(
                decision_id=f"{session.run.run_id}:decision:{loop_state.turn_count}",
                objective=turn_input.objective,
                reasoning_summary="No further deterministic actions are available.",
                actions=[],
                should_stop=True,
                requires_review=session.request.requires_review,
                metadata={"stop_reason": "no_action", "turn_index": turn_input.turn_index},
            )

        metadata = dict(turn_input.metadata)
        explicit_actions = metadata.get("actions")
        if isinstance(explicit_actions, list):
            actions = [RuntimeAction.model_validate(item) for item in explicit_actions if isinstance(item, dict)]
            return RuntimeDecision(
                decision_id=f"{session.run.run_id}:decision:0",
                objective=turn_input.objective,
                reasoning_summary="Using explicit actions from request metadata.",
                actions=actions,
                should_stop=not actions,
                requires_review=session.request.requires_review,
                metadata={"source": "explicit_actions", "turn_index": turn_input.turn_index},
            )

        actions: list[RuntimeAction] = []
        for index, tool_id in enumerate(turn_input.allowed_tools):
            actions.append(
                RuntimeAction(
                    action_id=f"{session.run.run_id}:tool:{index}",
                    kind="tool_call",
                    title=tool_id,
                    summary=f"Observe context using tool {tool_id}",
                    tool_id=tool_id,
                    inputs={
                        "partition": turn_input.partition,
                        "resource_id": turn_input.source_ref,
                        "objective": turn_input.objective,
                    },
                    metadata={"observation": True},
                    risk_level=session.request.risk_level,
                    requires_review=session.request.requires_review,
                )
            )
        if not actions:
            for index, skill_id in enumerate(turn_input.allowed_skills):
                actions.append(
                    RuntimeAction(
                        action_id=f"{session.run.run_id}:skill:{index}",
                        kind="skill_call",
                        title=skill_id,
                        summary=f"Execute preferred skill {skill_id}",
                        skill_id=skill_id,
                        inputs={"objective": turn_input.objective, "context": turn_input.context},
                        metadata={"preferred": True},
                        risk_level=session.request.risk_level,
                        requires_review=session.request.requires_review,
                    )
                )
        if not actions and turn_input.prompt.strip():
            actions.append(
                RuntimeAction(
                    action_id=f"{session.run.run_id}:respond:0",
                    kind="respond",
                    title="respond",
                    summary=turn_input.prompt,
                    prompt=turn_input.prompt,
                    inputs={"objective": turn_input.objective},
                    metadata={"source": "prompt"},
                    risk_level=session.request.risk_level,
                    requires_review=session.request.requires_review,
                )
            )
        return RuntimeDecision(
            decision_id=f"{session.run.run_id}:decision:0",
            objective=turn_input.objective,
            reasoning_summary="Built deterministic actions from request constraints.",
            actions=actions,
            should_stop=not actions,
            requires_review=session.request.requires_review,
            metadata={"source": "deterministic", "turn_index": turn_input.turn_index},
        )
