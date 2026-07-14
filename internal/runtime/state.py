"""Run-state model for runtime task execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from internal.models import RunArtifact
from internal.models.skill import SkillResult
from internal.models.tool import ToolResult
from internal.runtime.contracts import RuntimeDecision


@dataclass(slots=True)
class RuntimeRunState:
    """Mutable runtime state carried across one task run."""

    turn_count: int = 0
    decision_history: list[RuntimeDecision] = field(default_factory=list)
    applied_actions: list[str] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)
    skill_results: list[SkillResult] = field(default_factory=list)
    artifacts: list[RunArtifact] = field(default_factory=list)
    failure_messages: list[str] = field(default_factory=list)
    response_messages: list[str] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    should_stop: bool = False

    def record_decision(self, decision: RuntimeDecision) -> None:
        self.turn_count += 1
        self.decision_history.append(decision)

    def add_observation(self, *, kind: str, payload: dict[str, Any]) -> None:
        self.observations.append({"kind": kind, "payload": payload})

    def record_fact(self, key: str, value: Any) -> None:
        if key.strip():
            self.facts[key] = value
