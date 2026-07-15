"""Prompt-building contracts for runtime decision generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from internal.runtime.llm.decision_parser import build_runtime_decision_payload_schema
from internal.runtime.loop.planner_components import RuntimePlannerContext


@dataclass(slots=True)
class RuntimeDecisionPrompt:
    """Structured prompt payload handed to a future model adapter."""

    model: str = ""
    system: str = ""
    instruction: str = ""
    response_schema: dict[str, Any] = field(default_factory=dict)
    temperature: float = 0.0
    max_output_tokens: int = 1200
    context: dict[str, Any] = field(default_factory=dict)


class RuntimePromptBuilderPort(Protocol):
    """Build a model-facing prompt from the planner context."""

    def build_prompt(self, *, planner_context: RuntimePlannerContext) -> RuntimeDecisionPrompt:
        ...


class DefaultRuntimePromptBuilder:
    """Current prompt builder that emits a structured placeholder payload."""

    def __init__(self, *, model: str = "gpt-4o-mini", temperature: float = 0.0, max_output_tokens: int = 1200):
        self._model = model.strip() or "gpt-4o-mini"
        self._temperature = temperature
        self._max_output_tokens = max(1, int(max_output_tokens))

    def build_prompt(self, *, planner_context: RuntimePlannerContext) -> RuntimeDecisionPrompt:
        context_payload = {
            "objective": planner_context.objective,
            "prompt": planner_context.prompt,
            "partition": planner_context.partition,
            "source_type": planner_context.source_type,
            "source_ref": planner_context.source_ref,
            "task_payload": dict(planner_context.task_payload),
            "facts": dict(planner_context.facts),
            "observations": list(planner_context.observations),
            "completed_actions": list(planner_context.completed_actions),
            "recent_decisions": list(planner_context.recent_decisions),
            "recent_failures": list(planner_context.recent_failures),
            "latest_response": planner_context.latest_response,
            "allowed_tools": list(planner_context.allowed_tools),
            "allowed_skills": list(planner_context.allowed_skills),
            "risk_level": planner_context.risk_level,
            "requires_review": planner_context.requires_review,
            "remaining_step_budget": planner_context.remaining_step_budget,
            "remaining_tool_budget": planner_context.remaining_tool_budget,
            "remaining_skill_budget": planner_context.remaining_skill_budget,
            "hinted_actions": list(planner_context.hinted_actions),
            "hint_metadata": dict(planner_context.hint_metadata),
        }
        response_schema = build_runtime_decision_payload_schema()
        return RuntimeDecisionPrompt(
            model=self._model,
            system=(
                "You are a knowbase runtime planning agent. "
                "Return exactly one JSON object that matches the provided schema. "
                "Choose only actions that are explicitly allowed by the planner context budgets and whitelists."
            ),
            instruction=(
                "Inspect the runtime planner context and produce the next runtime decision.\n\n"
                "Rules:\n"
                "- Prefer the smallest safe next step.\n"
                "- Do not invent tool_id or skill_id outside the allowed lists.\n"
                "- If no safe action is available, set should_stop=true.\n"
                "- Keep reasoning_summary and action_plan_summary concise.\n"
                "- Return JSON only.\n\n"
                f"PlannerContext:\n{json.dumps(context_payload, ensure_ascii=True, indent=2)}\n\n"
                f"ResponseSchema:\n{json.dumps(response_schema, ensure_ascii=True, indent=2)}"
            ),
            response_schema=response_schema,
            temperature=self._temperature,
            max_output_tokens=self._max_output_tokens,
            context=context_payload,
        )


__all__ = [
    "RuntimeDecisionPrompt",
    "RuntimePromptBuilderPort",
    "DefaultRuntimePromptBuilder",
]
