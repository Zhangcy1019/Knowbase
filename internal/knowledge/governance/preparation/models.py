"""Models produced by the deterministic governance preparation stage."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from internal.knowledge.governance.proposal import GovernanceProposalContext
from internal.models.types import RunRiskLevel


class PartitionFacetCoverageAssessment(BaseModel):
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


class GovernanceRefreshScope(BaseModel):
    partition: str = ""
    scope: Literal["none", "affected_cases"] = "none"
    case_ids: list[str] = Field(default_factory=list)
    facet_keys: list[str] = Field(default_factory=list)
    reason: str = ""


class GovernancePreparation(BaseModel):
    """Complete deterministic preparation produced before governance runtime."""

    summary: str = ""
    risk_level: RunRiskLevel = "low"
    consistency_status: str = "unknown"
    consistency_mismatches: list[dict[str, object]] = Field(default_factory=list)
    facet_coverage_assessment: PartitionFacetCoverageAssessment | None = None
    proposal_context: GovernanceProposalContext | None = None
    refresh_scope: GovernanceRefreshScope | None = None
    notes: list[str] = Field(default_factory=list)


__all__ = ["GovernancePreparation", "PartitionFacetCoverageAssessment", "GovernanceRefreshScope"]
