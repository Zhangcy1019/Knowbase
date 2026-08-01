"""Structured batch-runtime models for lightweight backlog runtime runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field



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
    observed_facets: dict[str, list[str]] = Field(default_factory=dict)
    priority: int = 100


class ResourceEventGroup(BaseModel):
    group_id: str = ""
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    event_ids: list[str] = Field(default_factory=list)
    changed_fields: list[str] = Field(default_factory=list)
    related_resource_refs: list[str] = Field(default_factory=list)
    latest_event_at: datetime | None = None
    priority: int = 100
    is_cancelled_out: bool = False
    observed_facets: dict[str, list[str]] = Field(default_factory=dict)


class BatchWorkingSet(BaseModel):
    batch_id: str = ""
    partition: str = ""
    trigger_source: str = "manual"
    event_count: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    resource_groups: list[ResourceEventGroup] = Field(default_factory=list) # List of resource event groups in this batch
    affected_case_ids: list[str] = Field(default_factory=list) # List of case IDs that are affected by the events in this batch
    observed_facet_keys: list[str] = Field(default_factory=list) # Facet keys observed in event payloads; not necessarily changed keys.
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
