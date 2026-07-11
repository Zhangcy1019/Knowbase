"""Knowbase domain event schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from internal.models.types import KnowbaseEventType


class EventRelatedTarget(BaseModel):
    """One resource referenced by an event payload."""

    type: str
    id: str


class TextFieldChange(BaseModel):
    """Lightweight deterministic diff metadata for long text fields."""

    change_type: Literal["text_created", "text_updated", "text_deleted"] = "text_updated"
    before_length: int = 0
    after_length: int = 0


class CaseEventSnapshot(BaseModel):
    """Compact event snapshot for one case."""

    title: str = ""
    facet_count: int = 0
    facets: dict[str, list[str]] = Field(default_factory=dict)


class BaseResourceEventPayload(BaseModel):
    """Common event payload structure for resource lifecycle events."""

    change_kind: Literal["create", "update", "delete"]
    changed_fields: list[str] = Field(default_factory=list)
    related_targets: list[EventRelatedTarget] = Field(default_factory=list)


class CaseEventPayload(BaseResourceEventPayload):
    """Lifecycle payload for case events."""

    before: CaseEventSnapshot = Field(default_factory=CaseEventSnapshot)
    after: CaseEventSnapshot = Field(default_factory=CaseEventSnapshot)
    field_changes: dict[str, TextFieldChange] = Field(default_factory=dict)
    observed_facets: dict[str, list[str]] = Field(default_factory=dict)


class BacklogRequestPayload(BaseModel):
    """Synthetic payload used for explicit backlog drain and runtime dispatch requests."""

    request_kind: str = "runtime_request"
    summary: str = ""
    event_ids: list[str] = Field(default_factory=list)
    event_count: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    resource_refs: list[str] = Field(default_factory=list)
    trigger_source: str = ""
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


KnowbaseEventPayload = CaseEventPayload | BacklogRequestPayload


class KnowbaseEvent(BaseModel):
    """One domain event emitted by knowbase workflows."""

    event_type: KnowbaseEventType
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    occurred_at: datetime | None = None
    payload: KnowbaseEventPayload
