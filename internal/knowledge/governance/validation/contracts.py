"""Contracts for deterministic governance validation plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class GovernanceValidationContext:
    """Immutable evidence package passed to every validation plugin."""

    partition: str
    statistics: Any
    current_schema: Any
    candidate_schema: Any
    proposal: Any = None
    refresh_scope: Any = None


@dataclass(slots=True)
class GovernanceValidationResult:
    """Normalized result returned by one validation plugin."""

    plugin: str
    passed: bool = True
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "plugin": self.plugin,
            "passed": self.passed,
            "reasons": list(self.reasons),
            "metrics": dict(self.metrics),
        }


@dataclass(slots=True)
class GovernanceValidationReport:
    """Combined outcome of the enabled validation plugins."""

    passed: bool
    results: list[GovernanceValidationResult] = field(default_factory=list)

    @property
    def reasons(self) -> list[str]:
        return [reason for result in self.results for reason in result.reasons]

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": self.reasons,
            "plugins": [result.as_dict() for result in self.results],
        }


class GovernanceValidationPlugin(Protocol):
    """Protocol implemented by one deterministic governance constraint."""

    name: str

    def validate(self, *, context: GovernanceValidationContext) -> GovernanceValidationResult:
        ...
