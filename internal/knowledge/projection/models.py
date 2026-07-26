"""Models for deterministic case facet projection plans."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CaseProjectionChange(BaseModel):
    partition: str
    case_id: str
    before_facets: dict[str, list[str]] = Field(default_factory=dict)
    after_facets: dict[str, list[str]] = Field(default_factory=dict)
    changed_keys: list[str] = Field(default_factory=list)
    reason: str = "schema_projection"


class ProjectionPlan(BaseModel):
    partition: str
    target_case_ids: list[str] = Field(default_factory=list)
    changes: list[CaseProjectionChange] = Field(default_factory=list)
    unchanged_case_ids: list[str] = Field(default_factory=list)
    skipped_case_ids: list[str] = Field(default_factory=list)
    estimated_change_count: int = 0


__all__ = ["CaseProjectionChange", "ProjectionPlan"]
