"""Persistent event inbox models for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models.events import KnowbaseEventPayload
from internal.models.types import KnowbaseEventType


EventRecordStatus = Literal["recorded", "ready", "materialized", "completed", "failed", "ignored"]
EventDisposition = Literal["record_only", "immediate", "deferred", "batched", "ignore"]


class EventRecord(BaseModel):
    """One persisted domain event waiting for later scheduling or execution."""

    event_id: str = ""
    event_type: KnowbaseEventType | str
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    payload: KnowbaseEventPayload | dict[str, Any]
    status: EventRecordStatus = "recorded"
    disposition: EventDisposition = "record_only"
    priority: int = 100
    policy_id: str = ""
    ready_at: datetime | None = None
    next_retry_at: datetime | None = None
    last_run_at: datetime | None = None
    run_id: str = ""
    batch_key: str = ""
    attempt_count: int = 0
    error_message: str = ""
    occurred_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
