"""Aggregated backlog batch models for deferred maintenance runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from internal.models.event_record import EventRecord


class BacklogBatch(BaseModel):
    """One aggregated batch of backlog events submitted to runtime."""

    batch_id: str = ""
    partition: str = ""
    trigger_source: str = "manual"
    event_ids: list[str] = Field(default_factory=list)
    event_count: int = 0
    event_type_counts: dict[str, int] = Field(default_factory=dict)
    resource_refs: list[str] = Field(default_factory=list)
    assembled_at: datetime | None = None
    events: list[EventRecord] = Field(default_factory=list)
    summary: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
