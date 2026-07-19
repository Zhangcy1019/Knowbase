"""Cross-module ports for backlog/dispatch-facing capabilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from internal.models import EventRecord
if TYPE_CHECKING:
    from backlog.worker import EventWorkerRunResult


class EventBacklogPort(Protocol):
    """Stable backlog event admin surface used by runtime API routes."""

    def list_events(
        self,
        *,
        partition: str = "",
        status: str = "",
        event_type: str = "",
    ) -> list[EventRecord]:
        ...

    def get_event(self, event_id: str) -> EventRecord | None:
        ...

    def requeue_event(self, *, event_id: str) -> EventRecord:
        ...

    def delete_event(self, event_id: str) -> None:
        ...


class EventWorkerPort(Protocol):
    """Stable backlog drain surface used by runtime API routes."""

    async def run_once(
        self,
        *,
        partition: str = "",
        limit: int = 200,
        trigger_source: str = "manual",
    ) -> EventWorkerRunResult:
        ...


__all__ = [
    "EventBacklogPort",
    "EventWorkerPort",
]
