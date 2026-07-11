"""Minimal domain event publisher for knowbase."""

from __future__ import annotations

from internal.models import KnowbaseEvent

from .inbox_service import KnowbaseEventInboxService


class KnowbaseEventPublisher:
    """Publish domain events into the persistent inbox instead of executing them inline."""

    def __init__(
        self,
        *,
        inbox_service: KnowbaseEventInboxService,
    ):
        self._inbox_service = inbox_service

    async def publish(self, event: KnowbaseEvent) -> dict[str, object]:
        record = self._inbox_service.record_event(event=event)
        return {
            "event": record,
            "run": None,
            "artifacts": [],
            "skill_results": [],
        }
