"""Governance models for lightweight prepare/execute/finalize runtime runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field

from internal.models.types import RunRiskLevel


class PartitionFacetCoverageAssessment(BaseModel):
    """Partition-level assessment of whether current facet keys still fit recent cases."""

    partition: str = ""
    sampled_case_ids: list[str] = Field(default_factory=list)
    existing_keys: list[str] = Field(default_factory=list)
    touched_keys: list[str] = Field(default_factory=list)
    coverage_score: float = 0.0
    missing_key_signals: list[str] = Field(default_factory=list)
    ambiguous_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PartitionFacetSchemaProposal(BaseModel):
    """Suggested partition facet-schema evolution proposal."""

    partition: str = ""
    rationale: str = ""
    suggested_new_keys: list[str] = Field(default_factory=list)
    suggested_updated_keys: list[str] = Field(default_factory=list)
    suggested_removed_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PartitionRebuildRecommendation(BaseModel):
    """Recommended rebuild scope after assessing recent case/facet drift."""

    partition: str = ""
    rebuild_scope: Literal["none", "partial", "full"] = "none"
    target_case_ids: list[str] = Field(default_factory=list)
    target_facet_keys: list[str] = Field(default_factory=list)
    reason: str = ""
    estimated_change_count: int = 0
    risk_level: RunRiskLevel = "low"
    notes: list[str] = Field(default_factory=list)


@dataclass(slots=True)
class FacetGovernanceResult:
    """Complete decision produced by one facet-governance assessment."""

    coverage: PartitionFacetCoverageAssessment | None = None
    proposal: PartitionFacetSchemaProposal | None = None
    rebuild: PartitionRebuildRecommendation | None = None
    decision: str = "rejected"
    accepted_schema: object | None = None
    requires_review: bool = False
    risk_level: str = "low"
    reasons: list[str] = field(default_factory=list)
