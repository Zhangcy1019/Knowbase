"""Session and loop-state models for runtime runs."""

from __future__ import annotations

from dataclasses import dataclass, field

from internal.models import AgentRun, RunArtifact
from internal.models.skill import SkillResult
from internal.models.tool import ToolResult
from internal.runtime.contracts import RuntimeDecision, RuntimeRunRequest


@dataclass(slots=True)
class RuntimeSession:
    """Static context for one runtime run."""

    run: AgentRun
    request: RuntimeRunRequest


@dataclass(slots=True)
class RuntimeLoopState:
    """Mutable state for one runtime loop."""

    turn_count: int = 0
    decision_history: list[RuntimeDecision] = field(default_factory=list)
    applied_actions: list[str] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    skill_results: list[SkillResult] = field(default_factory=list)
    artifacts: list[RunArtifact] = field(default_factory=list)
    failure_messages: list[str] = field(default_factory=list)
    response_messages: list[str] = field(default_factory=list)
    should_stop: bool = False

    def record_decision(self, decision: RuntimeDecision) -> None:
        self.turn_count += 1
        self.decision_history.append(decision)
