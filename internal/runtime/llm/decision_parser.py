"""Decision-parsing contracts for runtime decision generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from internal.runtime.llm.decisioning import RuntimeDecisionDraft
    from internal.runtime.llm.prompt_builder import RuntimeDecisionPrompt


class RuntimeDecisionActionPayload(BaseModel):
    """Structured parser payload for one proposed action."""

    kind: str
    title: str = ""
    summary: str = ""
    target_ref: str = ""
    tool_id: str = ""
    skill_id: str = ""
    prompt: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    requires_review: bool = False
    action_id: str = ""


class RuntimeDecisionPayload(BaseModel):
    """Structured parser payload for one decision draft."""

    reasoning_summary: str = ""
    action_plan_summary: str = ""
    should_stop: bool = False
    stop_reason: str = "unknown"
    requires_review: bool = False
    review_reason: str = "unknown"
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    actions: list[RuntimeDecisionActionPayload] = Field(default_factory=list)


RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "reasoning_summary",
        "action_plan_summary",
        "should_stop",
        "stop_reason",
        "requires_review",
        "review_reason",
        "notes",
        "metadata",
        "actions",
    ],
    "properties": {
        "reasoning_summary": {"type": "string"},
        "action_plan_summary": {"type": "string"},
        "should_stop": {"type": "boolean"},
        "stop_reason": {
            "type": "string",
            "enum": [
                "completed",
                "no_action",
                "budget_exhausted",
                "requires_review",
                "waiting_for_observation",
                "unknown",
            ],
        },
        "requires_review": {"type": "boolean"},
        "review_reason": {
            "type": "string",
            "enum": [
                "unsafe_action",
                "insufficient_context",
                "policy_boundary",
                "manual_confirmation",
                "unknown",
            ],
        },
        "notes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "metadata": {"type": "object"},
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "kind",
                    "title",
                    "summary",
                    "target_ref",
                    "tool_id",
                    "skill_id",
                    "prompt",
                    "inputs",
                    "metadata",
                    "risk_level",
                    "requires_review",
                    "action_id",
                ],
                "properties": {
                    "kind": {
                        "type": "string",
                        "enum": ["tool_call", "skill_call", "respond", "stop"],
                    },
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "target_ref": {"type": "string"},
                    "tool_id": {"type": "string"},
                    "skill_id": {"type": "string"},
                    "prompt": {"type": "string"},
                    "inputs": {"type": "object"},
                    "metadata": {"type": "object"},
                    "risk_level": {"type": "string"},
                    "requires_review": {"type": "boolean"},
                    "action_id": {"type": "string"},
                },
            },
        },
    },
}


def build_runtime_decision_payload_schema() -> dict[str, Any]:
    """Return the canonical JSON schema for runtime decision payloads."""

    return dict(RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA)


class RuntimeDecisionParserPort(Protocol):
    """Parse a model-facing payload into a runtime decision draft."""

    def parse(self, *, prompt: RuntimeDecisionPrompt, payload: dict[str, Any]) -> "RuntimeDecisionDraft":
        ...


class DefaultRuntimeDecisionParser:
    """Parse a structured payload into a runtime decision draft."""

    def parse(self, *, prompt: RuntimeDecisionPrompt, payload: dict[str, Any]) -> "RuntimeDecisionDraft":
        del prompt
        normalized = RuntimeDecisionPayload.model_validate(payload)
        from internal.runtime.llm.decisioning import RuntimeDecisionDraft, RuntimeProposedAction

        return RuntimeDecisionDraft(
            reasoning_summary=normalized.reasoning_summary,
            action_plan_summary=normalized.action_plan_summary,
            should_stop=normalized.should_stop,
            stop_reason=normalized.stop_reason,  # type: ignore[arg-type]
            requires_review=normalized.requires_review,
            review_reason=normalized.review_reason,  # type: ignore[arg-type]
            notes=list(normalized.notes),
            metadata=dict(normalized.metadata),
            actions=[
                RuntimeProposedAction(
                    kind=item.kind,  # type: ignore[arg-type]
                    title=item.title,
                    summary=item.summary,
                    target_ref=item.target_ref,
                    tool_id=item.tool_id,
                    skill_id=item.skill_id,
                    prompt=item.prompt,
                    inputs=dict(item.inputs),
                    metadata=dict(item.metadata),
                    risk_level=item.risk_level,
                    requires_review=item.requires_review,
                    action_id=item.action_id,
                )
                for item in normalized.actions
            ],
        )


__all__ = [
    "RuntimeDecisionActionPayload",
    "RuntimeDecisionPayload",
    "RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA",
    "build_runtime_decision_payload_schema",
    "RuntimeDecisionParserPort",
    "DefaultRuntimeDecisionParser",
]
