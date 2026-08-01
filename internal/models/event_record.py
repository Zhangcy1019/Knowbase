"""Persistent event inbox models for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from internal.models.events import CaseEventPayload, KnowbaseEvent
from internal.models.types import KnowbaseEventType


EventRecordStatus = Literal["pending", "completed", "failed"]


class EventRecord(BaseModel):
    """One persisted domain event waiting for later scheduling or execution."""

    event_id: str = ""
    event_type: KnowbaseEventType | str
    partition: str = ""
    resource_type: str = ""
    resource_id: str = ""
    payload: CaseEventPayload
    status: EventRecordStatus = "pending"
    priority: int = 100
    next_retry_at: datetime | None = None
    last_run_at: datetime | None = None
    run_id: str = ""
    attempt_count: int = 0
    error_message: str = ""
    occurred_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_event(cls, event: KnowbaseEvent) -> "EventRecord":
        """Convert a published domain event into persisted inbox state."""
        return cls(
            event_type=event.event_type,
            partition=event.partition,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            payload=event.payload,
            occurred_at=event.occurred_at,
            status="pending",
            priority=100,
            next_retry_at=None,
            last_run_at=None,
            metadata={
                "source": "event_inbox",
                "intake_mode": "default_queue",
            },
        )
