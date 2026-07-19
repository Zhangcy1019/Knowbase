"""Primary runtime contracts for the agent harness direction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models import RunArtifact, RunStep, SkillResult, ToolResult


RuntimeRequestSource = Literal["backlog", "manual", "api", "scheduled", "system"]
RuntimeExecutionStatus = Literal["completed", "failed", "cancelled", "requires_review"]
RuntimeActionKind = Literal["tool_call", "skill_call"]
RuntimeStopReason = Literal["completed", "requires_review", "failed", "budget_exhausted", "no_action"]


class RuntimeRunRequest(BaseModel):
    """Structured request handed from backlog/dispatch into the runtime harness."""

    request_id: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    partition: str = ""

    objective: str = ""
    prompt: str = ""
    task_payload: dict[str, Any] = Field(default_factory=dict)
    task_hints: list[dict[str, Any]] = Field(default_factory=list)

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
    kind: RuntimeActionKind = "tool_call"
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


class RuntimeTaskContext(BaseModel):
    """Static task context exposed to the current agent turn."""

    objective: str = ""
    prompt: str = ""
    partition: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeExecutionBounds(BaseModel):
    """Execution boundaries and budgets for the current turn."""

    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    risk_level: str = "medium"
    requires_review: bool = False
    remaining_step_budget: int = 0
    remaining_tool_budget: int = 0
    remaining_skill_budget: int = 0


class RuntimeProgressSnapshot(BaseModel):
    """Condensed progress summary retained for agent planning."""

    completed_actions: list[str] = Field(default_factory=list)
    recent_decisions: list[str] = Field(default_factory=list)
    recent_failures: list[str] = Field(default_factory=list)
    latest_response: str = ""


class RuntimeAgentHints(BaseModel):
    """Planner hints explicitly surfaced to the runtime agent."""

    actions: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeTurnInput(BaseModel):
    """Structured agent-facing view for one loop turn."""

    run_id: str = ""
    request_id: str = ""
    turn_index: int = 0
    # task: static context for the current turn
    task: RuntimeTaskContext = Field(default_factory=RuntimeTaskContext)
    # memory: working memory snapshot for the current turn
    memory: RuntimeMemorySnapshot = Field(default_factory=RuntimeMemorySnapshot)
    # bounds: execution boundaries and budgets for the current turn
    bounds: RuntimeExecutionBounds = Field(default_factory=RuntimeExecutionBounds)
    # progress: condensed progress summary for the current turn
    progress: RuntimeProgressSnapshot = Field(default_factory=RuntimeProgressSnapshot)
    # hints: planner hints explicitly surfaced to the runtime agent
    hints: RuntimeAgentHints = Field(default_factory=RuntimeAgentHints)


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
