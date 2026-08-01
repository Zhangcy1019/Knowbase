"""Primary runtime contracts for the agent harness direction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models import RunArtifact, RunStep, SkillResult, SkillSpec, ToolResult, ToolSpec
from internal.runtime.verification.profile import RuntimeVerificationProfile


RuntimeRequestSource = Literal["backlog", "manual", "api", "scheduled", "system"]
RuntimeExecutionStatus = Literal["completed", "failed", "cancelled", "requires_review"]
RuntimeStopReason = Literal["completed", "requires_review", "failed", "budget_exhausted", "no_action"]


class RuntimeRepairPolicy(BaseModel):
    """Bounded retry policy for verification-driven repair rounds."""

    max_repair_rounds: int = 0


class RuntimeAcceptanceSpec(BaseModel):
    """Acceptance requirements attached to one runtime request."""

    completion_checks: list[str] = Field(default_factory=list)
    max_retries: int = 0
    repair_policy: RuntimeRepairPolicy = Field(default_factory=RuntimeRepairPolicy)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RuntimeStopPolicy(BaseModel):
    """Explicit stop conditions that shape runtime termination behavior."""

    stop_when_acceptance_satisfied: bool = False
    stop_when_no_executable_action: bool = False

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RuntimeRiskPolicy(BaseModel):
    """Risk-policy hints surfaced to planning and verification layers."""

    risk_level: str = "medium"

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RuntimeWorkProfile(BaseModel):
    """Primary work-phase contract attached to one runtime request."""

    objective: str = ""
    mission_summary: str = ""
    instructions: list[str] = Field(default_factory=list)
    input_context: dict[str, Any] = Field(default_factory=dict)
    capability_hints: list[dict[str, Any]] = Field(default_factory=list)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    max_steps: int = 16
    max_tool_calls: int = 24
    max_skill_calls: int = 8


class RuntimeRunRequest(BaseModel):
    """Structured request handed from backlog/dispatch into the runtime harness."""

    request_id: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    partition: str = ""

    work: RuntimeWorkProfile = Field(default_factory=RuntimeWorkProfile)
    acceptance: RuntimeAcceptanceSpec = Field(default_factory=RuntimeAcceptanceSpec)
    verification: RuntimeVerificationProfile = Field(default_factory=RuntimeVerificationProfile)
    stop_policy: RuntimeStopPolicy = Field(default_factory=RuntimeStopPolicy)
    risk_policy: RuntimeRiskPolicy = Field(default_factory=RuntimeRiskPolicy)

    risk_level: str = "medium"
    requires_review: bool = False

    metadata: dict[str, Any] = Field(default_factory=dict)

    def resolved_verification_profile(self) -> RuntimeVerificationProfile:
        profile = self.verification.model_copy()
        if profile.max_retries == 0 and self.acceptance.max_retries:
            profile.max_retries = self.acceptance.max_retries
        if not profile.require_acceptance and self.stop_policy.stop_when_acceptance_satisfied:
            profile.require_acceptance = True
        profile.allowed_skills = [item for item in profile.allowed_skills if str(item).strip()]
        profile.allowed_tools = [item for item in profile.allowed_tools if str(item).strip()]
        return profile


class RuntimeAction(BaseModel):
    """One atomic action emitted by the planner and executed by the runtime."""

    action_id: str = ""
    title: str = ""
    summary: str = ""
    capability_id: str = ""
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
    mission_summary: str = ""
    instructions: list[str] = Field(default_factory=list)
    partition: str = ""
    source_type: RuntimeRequestSource = "manual"
    source_ref: str = ""
    work: RuntimeWorkProfile = Field(default_factory=RuntimeWorkProfile)
    input_context: dict[str, Any] = Field(default_factory=dict)
    output_contract: dict[str, Any] = Field(default_factory=dict)
    acceptance: RuntimeAcceptanceSpec = Field(default_factory=RuntimeAcceptanceSpec)
    verification: RuntimeVerificationProfile = Field(default_factory=RuntimeVerificationProfile)
    stop_policy: RuntimeStopPolicy = Field(default_factory=RuntimeStopPolicy)
    risk_policy: RuntimeRiskPolicy = Field(default_factory=RuntimeRiskPolicy)
    verification_skills: list[str] = Field(default_factory=list)
    verification_tools: list[str] = Field(default_factory=list)


class RuntimeExecutionBounds(BaseModel):
    """Execution boundaries and budgets for the current turn."""

    allowed_tools: list[str] = Field(default_factory=list)
    allowed_skills: list[str] = Field(default_factory=list)
    allowed_verification_tools: list[str] = Field(default_factory=list)
    allowed_verification_skills: list[str] = Field(default_factory=list)
    available_tool_specs: list[ToolSpec] = Field(default_factory=list)
    available_skill_specs: list[SkillSpec] = Field(default_factory=list)
    available_verification_tool_specs: list[ToolSpec] = Field(default_factory=list)
    available_verification_skill_specs: list[SkillSpec] = Field(default_factory=list)
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
