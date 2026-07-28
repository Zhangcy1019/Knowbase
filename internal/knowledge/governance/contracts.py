"""Cross-stage contracts shared by the governance workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.knowledge.governance.preparation.models import (
    PartitionFacetCoverageAssessment,
    GovernanceRefreshScope,
)
from internal.knowledge.governance.proposal.models import PartitionFacetSchemaProposal
from internal.knowledge.statistics.models import CaseStatisticsSnapshot, QueryStatisticsSnapshot


GovernanceDecision = Literal["no_change", "accepted", "rejected", "requires_review", "failed"]


class GovernanceStatisticsInput(BaseModel):
    case: CaseStatisticsSnapshot | None = None
    query: QueryStatisticsSnapshot | None = None


class GovernanceEvidence(BaseModel):
    coverage: PartitionFacetCoverageAssessment | None = None
    proposal: PartitionFacetSchemaProposal | None = None
    refresh_scope: GovernanceRefreshScope | None = None
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
    coverage: PartitionFacetCoverageAssessment | None = None
    proposal: PartitionFacetSchemaProposal | None = None
    refresh_scope: GovernanceRefreshScope | None = None
    decision: GovernanceDecision = "no_change"
    accepted_schema: object | None = None
    requires_review: bool = False
    risk_level: str = "low"
    reasons: list[str] = field(default_factory=list)
    reason_details: list[dict[str, Any]] = field(default_factory=list)
    evidence: GovernanceEvidence | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
