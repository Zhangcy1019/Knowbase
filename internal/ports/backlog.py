"""Cross-module ports for backlog/dispatch-facing capabilities."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol

from internal.models import EventRecord
if TYPE_CHECKING:
    from internal.backlog.worker import EventWorkerRunResult


class EventBacklogPort(Protocol):
    """Stable backlog storage and batch-lifecycle surface."""

    def assemble_batch(self, *, partition: str = "", trigger_source: str = "manual", limit: int = 200) -> Any:
        ...

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

    def mark_batch_running(self, *, event_ids: list[str]) -> list[EventRecord]:
        ...

    def complete_batch(
        self,
        *,
        event_ids: list[str],
        run_id: str = "",
        last_run_at: datetime | None = None,
    ) -> list[EventRecord]:
        ...

    def fail_batch(
        self,
        *,
        event_ids: list[str],
        error_message: str,
        next_retry_at: datetime | None,
        last_run_at: datetime | None = None,
    ) -> list[EventRecord]:
        ...


class EventWorkerPort(Protocol):
    """Drain surface that submits batches to Knowledge asynchronously."""

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
