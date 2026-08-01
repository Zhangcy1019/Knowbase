"""Contracts for deterministic schema-proposal discovery plugins."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol, Any

from pydantic import BaseModel, ConfigDict, Field

from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal


class GovernanceProposalContext(BaseModel):
    """Read-only signals available to every proposal plugin."""

    model_config = ConfigDict(frozen=True)

    partition: str
    scenario_description: str
    existing_facet_keys: list[str]
    observed_facet_keys: list[str]
    semantic_candidate_keys: list[str]
    missing_key_signals: list[str]
    stable_key_gaps: list[str]
    semantic_index_key_counts: dict[str, int]
    facet_index_key_counts: dict[str, int]
    semantic_index_case_count: int
    statistics_case_count: int = 0
    statistics_semantic_key_counts: dict[str, int] = Field(default_factory=dict)
    statistics_facet_key_counts: dict[str, int] = Field(default_factory=dict)
    consistency_status: str = "unknown"
    consistency_mismatches: list[dict[str, Any]] = Field(default_factory=list)
    affected_case_count: int = 0


@dataclass(slots=True)
class GovernanceProposalPluginResult:
    """The isolated contribution and diagnostics of one plugin."""

    plugin: str
    suggested_new_keys: list[str] = field(default_factory=list)
    suggested_removed_keys: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    root_cause: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "plugin": self.plugin,
            "suggested_new_keys": list(self.suggested_new_keys),
            "suggested_removed_keys": list(self.suggested_removed_keys),
            "reasons": list(self.reasons),
            "root_cause": self.root_cause,
            "evidence": dict(self.evidence),
            "metrics": dict(self.metrics),
        }


@dataclass(slots=True)
class GovernanceProposalConflict:
    """Conflicting candidate actions emitted for the same schema key."""

    key: str
    candidates: list[str] = field(default_factory=list)
    plugins: list[str] = field(default_factory=list)
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "candidates": list(self.candidates),
            "plugins": list(self.plugins),
            "reason": self.reason,
        }


@dataclass(slots=True)
class GovernanceProposalReport:
    """Merged proposal plus per-plugin diagnostics."""

    proposal: PartitionFacetSchemaProposal
    results: list[GovernanceProposalPluginResult] = field(default_factory=list)
    status: Literal["no_change", "proposed", "blocked"] = "no_change"
    conflicts: list[GovernanceProposalConflict] = field(default_factory=list)
    impact: dict[str, Any] = field(default_factory=dict)
    reason_details: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_effective_proposal(self) -> bool:
        return any(
            (
                self.proposal.suggested_new_keys,
                self.proposal.suggested_removed_keys,
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal": self.proposal.model_dump(),
            "status": self.status,
            "has_effective_proposal": self.has_effective_proposal,
            "conflicts": [item.as_dict() for item in self.conflicts],
            "impact": dict(self.impact),
            "reason_details": list(self.reason_details),
            "plugins": [result.as_dict() for result in self.results],
        }


def has_effective_schema_proposal(proposal: PartitionFacetSchemaProposal | None) -> bool:
    """Return whether a proposal contains at least one actionable candidate."""
    if proposal is None:
        return False
    return any(
        (
            proposal.suggested_new_keys,
            proposal.suggested_removed_keys,
        )
    )


class GovernanceProposalPlugin(Protocol):
    """Protocol implemented by one deterministic proposal detector."""

    name: str

    def propose(self, *, context: GovernanceProposalContext) -> GovernanceProposalPluginResult:
        ...
