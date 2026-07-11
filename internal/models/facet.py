"""Facet-oriented models for the new knowbase organization layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PartitionFacetDefinition(BaseModel):
    """Definition of one stable facet key inside a partition."""

    key: str
    display_name: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    enabled: bool = True


class PartitionFacetSchema(BaseModel):
    """Partition-scoped stable facet schema."""

    definitions: list[PartitionFacetDefinition] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class CaseFacetValuesChangeRecord(BaseModel):
    """Audit record for one case-level facet-value change."""

    change_id: str
    partition: str
    case_id: str
    before_values: dict[str, list[str]] = Field(default_factory=dict)
    after_values: dict[str, list[str]] = Field(default_factory=dict)
    reason: str = ""
    source_event_ids: list[str] = Field(default_factory=list)
    run_id: str = ""
    created_at: datetime


class PartitionFacetValueListChangeRecord(BaseModel):
    """Audit record for one partition facet value-list change."""

    change_id: str
    partition: str
    facet_key: str
    before_values: list[str] = Field(default_factory=list)
    after_values: list[str] = Field(default_factory=list)
    added_values: list[str] = Field(default_factory=list)
    removed_values: list[str] = Field(default_factory=list)
    reason: str = ""
    source_event_ids: list[str] = Field(default_factory=list)
    run_id: str = ""
    created_at: datetime
