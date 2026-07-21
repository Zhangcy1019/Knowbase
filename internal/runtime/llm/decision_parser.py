"""Decision-parsing contracts for runtime decision generation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from pydantic import BaseModel, Field, model_validator

if TYPE_CHECKING:
    from internal.runtime.llm.decisioning import RuntimeDecisionDraft
    from internal.runtime.llm.prompt_builder import RuntimeDecisionPrompt


class RuntimeDecisionActionPayload(BaseModel):
    """Structured parser payload for one proposed action."""

    capability_id: str
    title: str = ""
    summary: str = ""
    target_ref: str = ""
    prompt: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    requires_review: bool = False
    action_id: str = ""

    @model_validator(mode="before")
    @classmethod
    def _normalize_nullable_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for field_name in (
            "capability_id",
            "title",
            "summary",
            "target_ref",
            "prompt",
            "risk_level",
            "action_id",
        ):
            if normalized.get(field_name) is None:
                normalized[field_name] = ""
        if normalized.get("inputs") is None:
            normalized["inputs"] = {}
        if normalized.get("metadata") is None:
            normalized["metadata"] = {}
        if normalized.get("requires_review") is None:
            normalized["requires_review"] = False
        return normalized


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

    @model_validator(mode="before")
    @classmethod
    def _normalize_nullable_fields(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for field_name in (
            "reasoning_summary",
            "action_plan_summary",
            "stop_reason",
            "review_reason",
        ):
            if normalized.get(field_name) is None:
                normalized[field_name] = ""
        if normalized.get("metadata") is None:
            normalized["metadata"] = {}
        if normalized.get("notes") is None:
            normalized["notes"] = []
        if normalized.get("actions") is None:
            normalized["actions"] = []
        if normalized.get("should_stop") is None:
            normalized["should_stop"] = False
        if normalized.get("requires_review") is None:
            normalized["requires_review"] = False
        return normalized


RUNTIME_DECISION_PAYLOAD_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "should_stop",
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
                    "capability_id",
                    "inputs",
                ],
                "properties": {
                    "capability_id": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "target_ref": {"type": "string"},
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
                    capability_id=item.capability_id,
                    title=item.title,
                    summary=item.summary,
                    target_ref=item.target_ref,
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
