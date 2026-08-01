"""Governance models for lightweight prepare/execute/finalize runtime runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.knowledge.governance.contracts import GovernanceStatisticsInput
from internal.knowledge.governance.preparation.models import (
    PartitionFacetCoverageAssessment as PreparationFacetCoverageAssessment,
    GovernanceRefreshScope as PreparationRefreshScope,
)
from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal as ProposalSchemaProposal


GovernanceDecision = Literal["no_change", "accepted", "rejected", "requires_review", "failed"]


class PartitionFacetCoverageAssessment(BaseModel):
    """Partition-level assessment of current and affected-case facet coverage."""

    partition: str = ""
    affected_case_ids: list[str] = Field(default_factory=list)
    existing_facet_keys: list[str] = Field(default_factory=list)
    observed_facet_keys: list[str] = Field(default_factory=list)
    coverage_score: float | None = None
    baseline_coverage: float | None = None
    affected_case_coverage: float | None = None
    post_batch_coverage: float | None = None
    coverage_delta: float | None = None
    coverage_status: Literal["not_applicable", "available", "incomplete", "inconsistent"] = "not_applicable"
    missing_key_signals: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PartitionFacetSchemaProposal(BaseModel):
    """Suggested partition facet-schema evolution proposal."""

    partition: str = ""
    rationale: str = ""
    suggested_new_keys: list[str] = Field(default_factory=list)
    suggested_removed_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GovernanceEvidence(BaseModel):
    """Read-only evidence passed between preparation and governance decision."""

    coverage: PreparationFacetCoverageAssessment | None = None
    proposal: ProposalSchemaProposal | None = None
    refresh_scope: PreparationRefreshScope | None = None
    statistics_summary: dict[str, Any] = Field(default_factory=dict)
    proposal_diagnostics: list[dict[str, Any]] = Field(default_factory=list)
    preparation_notes: list[str] = Field(default_factory=list)
    consistency_status: str = "unknown"
    consistency_mismatches: list[dict[str, Any]] = Field(default_factory=list)
    proposal_status: str = "unknown"
    proposal_conflicts: list[dict[str, Any]] = Field(default_factory=list)
    proposal_impact: dict[str, Any] = Field(default_factory=dict)
    proposal_reason_details: list[dict[str, Any]] = Field(default_factory=list)


@dataclass(slots=True)
class GovernanceResult:
    """Complete decision produced by one governance assessment."""

    coverage: PartitionFacetCoverageAssessment | None = None
    proposal: PartitionFacetSchemaProposal | None = None
    refresh_scope: PreparationRefreshScope | None = None
    decision: GovernanceDecision = "no_change"
    accepted_schema: object | None = None
    requires_review: bool = False
    risk_level: str = "low"
    reasons: list[str] = field(default_factory=list)
    reason_details: list[dict[str, Any]] = field(default_factory=list)
    evidence: GovernanceEvidence | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Transitional module-level exports kept while callers move to stage-owned
# model modules. These are aliases, not duplicate model definitions.
PartitionFacetCoverageAssessment = PreparationFacetCoverageAssessment
PartitionFacetSchemaProposal = ProposalSchemaProposal
GovernanceRefreshScope = PreparationRefreshScope
