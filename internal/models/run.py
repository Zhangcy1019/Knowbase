"""Agent-run runtime models for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from internal.models.types import AgentRunMode, AgentRunStatus, RunRiskLevel


class AgentRun(BaseModel):
    """One runtime session handling an event or backlog/runtime request."""

    run_id: str = ""
    partition: str = ""
    agent_id: str = ""
    mode: AgentRunMode = "agent"
    status: AgentRunStatus = "pending"
    source_type: str = "event"
    source_event_type: str = ""
    source_event_id: str = ""
    source_ref: str = ""
    objective: str = ""
    reasoning_summary: str = ""
    final_summary: str = ""
    planning_context: dict[str, Any] = Field(default_factory=dict)
    tool_whitelist: list[str] = Field(default_factory=list)
    skill_whitelist: list[str] = Field(default_factory=list)
    step_count: int = 0
    tool_call_count: int = 0
    skill_call_count: int = 0
    max_steps: int = 12
    max_tool_calls: int = 20
    max_skill_calls: int = 6
    risk_level: RunRiskLevel = "medium"
    requires_review: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    finished_at: datetime | None = None


class RunStep(BaseModel):
    """One auditable step within an agent run."""

    step_id: str = ""
    run_id: str
    index: int = 0
    step_type: str
    name: str = ""
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""
    created_at: datetime | None = None


class RunArtifact(BaseModel):
    """Structured intermediate or final artifact emitted by one run."""

    artifact_id: str = ""
    run_id: str
    artifact_type: str
    title: str = ""
    content: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
