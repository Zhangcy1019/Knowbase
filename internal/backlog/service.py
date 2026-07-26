"""Facade service for backlog reads and dispatch execution entrypoints."""

from __future__ import annotations

from internal.backlog.events.queue import KnowbaseEventBacklogService
from internal.backlog.events.worker import EventWorkerRunResult, KnowbaseEventWorker


class KnowbaseEventService:
    """Unified service surface for backlog reads and drain entrypoints."""

    def __init__(
        self,
        *,
        backlog_service: KnowbaseEventBacklogService,
        worker: KnowbaseEventWorker,
    ):
        self._backlog_service = backlog_service
        self._worker = worker

    def backlog(self) -> KnowbaseEventBacklogService:
        return self._backlog_service

    async def drain(self, *, partition: str = "", limit: int = 200, trigger_source: str = "manual") -> EventWorkerRunResult:
        return await self._worker.run_once(partition=partition, limit=limit, trigger_source=trigger_source)
