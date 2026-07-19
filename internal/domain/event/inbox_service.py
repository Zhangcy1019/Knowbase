"""Record domain events into the knowbase inbox."""

from __future__ import annotations

from internal.models import EventRecord, KnowbaseEvent

class KnowbaseEventInboxService:
    """Persist domain events before any later scheduling or execution."""

    def __init__(
        self,
        *,
        repository,
    ):
        self._repository = repository

    def record_event(self, *, event: KnowbaseEvent) -> EventRecord:
        status = "pending"
        return self._repository.save(
            EventRecord(
                event_type=event.event_type,
                partition=event.partition,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                payload=event.payload,
                occurred_at=event.occurred_at,
                status=status,
                priority=100,
                policy_id="",
                ready_at=None,
                next_retry_at=None,
                last_run_at=None,
                metadata={
                    "source": "event_inbox",
                    "intake_mode": "default_queue",
                },
            )
        )
