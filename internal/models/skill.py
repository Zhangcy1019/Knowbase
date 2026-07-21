"""Skill-oriented runtime models for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SkillExecutionMode = Literal["deterministic", "plan", "agent"]
SkillSideEffectScope = Literal["read_only", "single_resource", "partition", "cross_partition", "external"]


class SkillSpec(BaseModel):
    """Describe one skill that can be selected by an agent or runtime planner."""

    skill_id: str
    title: str = ""
    description: str = ""
    execution_mode: SkillExecutionMode = "deterministic"
    side_effect_scope: SkillSideEffectScope = "single_resource"
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    examples: list[dict[str, Any]] = Field(default_factory=list)
    usage_notes: list[str] = Field(default_factory=list)
    argument_binding_hints: dict[str, str] = Field(default_factory=dict)


class SkillInvocation(BaseModel):
    """One concrete skill invocation to be executed by the runtime."""

    invocation_id: str = ""
    skill_id: str
    partition: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillResult(BaseModel):
    """Structured output produced by one skill invocation."""

    invocation_id: str = ""
    skill_id: str
    ok: bool = True
    updated_objects: list[str] = Field(default_factory=list)
    output: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""
    started_at: datetime | None = None
    finished_at: datetime | None = None
