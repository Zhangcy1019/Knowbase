"""Aggregated runtime trace models for replay and frontend reconstruction."""

from __future__ import annotations

from pydantic import BaseModel, Field

from internal.models.run import AgentRun, RunArtifact, RunStep


class RuntimeTraceTurn(BaseModel):
    """One reconstructed runtime turn with attached artifacts."""

    turn_index: int = 0
    decision_step: RunStep | None = None
    decision_artifact: RunArtifact | None = None
    planner_context_artifact: RunArtifact | None = None
    llm_prompt_artifact: RunArtifact | None = None
    llm_response_artifact: RunArtifact | None = None
    action_steps: list[RunStep] = Field(default_factory=list)
    tool_calls: list[RunStep] = Field(default_factory=list)
    tool_results: list[RunStep] = Field(default_factory=list)
    skill_calls: list[RunStep] = Field(default_factory=list)
    skill_results: list[RunStep] = Field(default_factory=list)
    errors: list[RunStep] = Field(default_factory=list)


class RuntimeTraceReplay(BaseModel):
    """Complete reconstructed trace for one runtime run."""

    run: AgentRun
    request_artifact: RunArtifact | None = None
    turns: list[RuntimeTraceTurn] = Field(default_factory=list)
    steps: list[RunStep] = Field(default_factory=list)
    artifacts: list[RunArtifact] = Field(default_factory=list)


__all__ = [
    "RuntimeTraceReplay",
    "RuntimeTraceTurn",
]
