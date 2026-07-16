"""Knowledge-owned task models that bridge backlog batches into runtime runs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeTaskActionHint(BaseModel):
    """One business-owned action hint exposed to the runtime planner."""

    kind: str = ""
    action_id: str = ""
    title: str = ""
    summary: str = ""
    tool_id: str = ""
    skill_id: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    requires_review: bool = False


class KnowledgeTask(BaseModel):
    """Structured business task prepared by knowledge before runtime execution."""

    task_id: str = ""
    source_batch_id: str = ""
    source_type: str = "backlog"
    partition: str = ""
    domain: str = "backlog_maintenance"
    objective: str = ""
    prompt: str = ""
    task_payload: dict[str, Any] = Field(default_factory=dict)
    action_hints: list[KnowledgeTaskActionHint] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    max_steps: int = 16
    max_tool_calls: int = 24
    max_skill_calls: int = 8
    risk_level: str = "medium"
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "KnowledgeTask",
    "KnowledgeTaskActionHint",
]
