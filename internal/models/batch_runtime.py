"""Structured batch-runtime models for lightweight backlog runtime runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models.governance import (
    PartitionFacetCoverageAssessment,
    PartitionFacetSchemaProposal,
    PartitionRebuildRecommendation,
)
from internal.models.types import RunRiskLevel


class NormalizedEvent(BaseModel):
    event_id: str = ""
    event_type: str = ""
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    change_kind: str = ""
    occurred_at: datetime | None = None
    changed_fields: list[str] = Field(default_factory=list)
    field_changes: dict[str, Any] = Field(default_factory=dict)
    related_resource_refs: list[str] = Field(default_factory=list)
    priority: int = 100
    payload: dict[str, Any] = Field(default_factory=dict)


class ResourceEventGroup(BaseModel):
    group_id: str = ""
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    event_ids: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)
    dominant_change_kind: str = ""
    changed_fields: list[str] = Field(default_factory=list)
    related_resource_refs: list[str] = Field(default_factory=list)
    latest_event_at: datetime | None = None
    priority: int = 100
    collapsed_event_count: int = 0
    has_create: bool = False
    has_update: bool = False
    has_delete: bool = False
    is_cancelled_out: bool = False
    observed_facets: dict[str, list[str]] = Field(default_factory=dict)
    summary: str = ""


class BatchWorkingSet(BaseModel):
    batch_id: str = ""
    partition: str = ""
    trigger_source: str = "manual"
    event_count: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    normalized_events: list[NormalizedEvent] = Field(default_factory=list)
    resource_groups: list[ResourceEventGroup] = Field(default_factory=list)
    affected_case_ids: list[str] = Field(default_factory=list)
    affected_facet_keys: list[str] = Field(default_factory=list)
    affected_resource_refs: list[str] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchActionCandidate(BaseModel):
    candidate_id: str = ""
    target_type: str = ""
    target_id: str = ""
    action_type: Literal[
        "assess_partition_facets",
        "refresh_selected_case_representation",
        "refresh_selected_case_facets",
        "generate_facet_promotion_candidate",
        "review_facet_schema_evolution",
        "ignore",
    ] = "ignore"
    source_event_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    risk_level: RunRiskLevel = "low"
    requires_review: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchPreparation(BaseModel):
    summary: str = ""
    risk_level: RunRiskLevel = "low"
    requires_review: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    candidates: list[BatchActionCandidate] = Field(default_factory=list)
    facet_coverage_assessment: PartitionFacetCoverageAssessment | None = None
    schema_proposal: PartitionFacetSchemaProposal | None = None
    rebuild_recommendation: PartitionRebuildRecommendation | None = None
    notes: list[str] = Field(default_factory=list)


class BatchWorkItem(BaseModel):
    work_item_id: str = ""
    target_type: str = ""
    target_id: str = ""
    skill_id: str = ""
    inputs: dict[str, Any] = Field(default_factory=dict)
    source_event_ids: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    risk_level: RunRiskLevel = "low"
    needs_review: bool = False
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchExecutionPlan(BaseModel):
    summary: str = ""
    risk_level: RunRiskLevel = "low"
    requires_review: bool = False
    work_items: list[BatchWorkItem] = Field(default_factory=list)
    rebuild_recommendation: PartitionRebuildRecommendation | None = None
    notes: list[str] = Field(default_factory=list)
