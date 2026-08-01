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
        return self._repository.save(EventRecord.from_event(event))
