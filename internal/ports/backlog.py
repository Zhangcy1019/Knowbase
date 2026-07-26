"""Cross-module ports for backlog/dispatch-facing capabilities."""

from __future__ import annotations

from datetime import datetime
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Protocol

from internal.models import EventRecord
if TYPE_CHECKING:
    from internal.backlog.events.worker import EventWorkerRunResult


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
        size: int = 500,
    ) -> list[EventRecord]:
        ...

    def get_event(self, event_id: str) -> EventRecord | None:
        ...

    def mark_ready(self, *, event_id: str) -> EventRecord:
        ...

    def mark_ignored(self, *, event_id: str) -> EventRecord:
        ...

    def requeue_event(self, *, event_id: str) -> EventRecord:
        ...

    def delete_event(self, event_id: str) -> None:
        ...

    def list_ready_events(self, *, partition: str = "", limit: int = 100) -> list[EventRecord]:
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


class PartitionTaskQueuePort(Protocol):
    """Schedule commands serially within each partition."""

    def enqueue(
        self,
        *,
        partition: str,
        kind: str,
        handler: Callable[[Any], Awaitable[None]],
        payload: dict[str, Any] | None = None,
    ) -> Any:
        ...

    async def wait_idle(self, *, partition: str) -> None:
        ...

    def get(self, task_id: str) -> Any | None:
        ...


__all__ = [
    "EventBacklogPort",
    "EventWorkerPort",
    "PartitionTaskQueuePort",
]
