"""Primary runtime contracts for the agent harness direction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models import RunArtifact, RunStep, SkillResult, ToolResult


RuntimeRequestSource = Literal["backlog", "manual", "api", "scheduled", "system"]
RuntimeExecutionStatus = Literal["completed", "failed", "cancelled", "requires_review"]
RuntimeActionKind = Literal["tool_call", "skill_call", "respond", "stop"]
RuntimeStopReason = Literal["completed", "requires_review", "failed", "budget_exhausted", "no_action"]


class RuntimeRunRequest(BaseModel):
    """Structured request handed from backlog/dispatch into the runtime harness."""

    request_id: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    partition: str = ""
    objective: str = ""
    prompt: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    max_steps: int = 16
    max_tool_calls: int = 24
    max_skill_calls: int = 8
    risk_level: str = "medium"
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeAction(BaseModel):
    """One atomic action emitted by the planner and executed by the runtime."""

    action_id: str = ""
    kind: RuntimeActionKind = "respond"
    title: str = ""
    summary: str = ""
    tool_id: str = ""
    skill_id: str = ""
    prompt: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "medium"
    requires_review: bool = False


class RuntimeDecision(BaseModel):
    """One planner decision produced for one loop turn."""

    decision_id: str = ""
    objective: str = ""
    reasoning_summary: str = ""
    actions: list[RuntimeAction] = Field(default_factory=list)
    should_stop: bool = False
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeObservation(BaseModel):
    """One normalized observation retained in runtime memory."""

    kind: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeMemorySnapshot(BaseModel):
    """Serializable snapshot of working memory exposed to the agent."""

    facts: dict[str, Any] = Field(default_factory=dict)
    observations: list[RuntimeObservation] = Field(default_factory=list)


class RuntimeTurnInput(BaseModel):
    """Structured per-turn payload passed into the agent."""

    run_id: str = ""
    request_id: str = ""
    turn_index: int = 0
    objective: str = ""
    prompt: str = ""
    partition: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    context: dict[str, Any] = Field(default_factory=dict)
    memory: RuntimeMemorySnapshot = Field(default_factory=RuntimeMemorySnapshot)
    prior_decisions: list[RuntimeDecision] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    requires_review: bool = False
    remaining_step_budget: int = 0
    remaining_tool_budget: int = 0
    remaining_skill_budget: int = 0
    failure_messages: list[str] = Field(default_factory=list)
    response_messages: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeRunResult(BaseModel):
    """Structured result emitted by the runtime harness after one run."""

    request_id: str = ""
    run_id: str = ""
    status: RuntimeExecutionStatus = "completed"
    final_summary: str = ""
    reasoning_summary: str = ""
    steps: list[RunStep] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)
    skill_results: list[SkillResult] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
    applied_actions: list[str] = Field(default_factory=list)
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
