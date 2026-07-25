"""Worker helpers for draining persisted backlog batches."""

from __future__ import annotations

from pydantic import BaseModel, Field

from internal.ports import KnowledgeBatchNotificationPort
from internal.utils.logger import get_logger

from .queue import KnowbaseEventBacklogService


logger = get_logger("knowbase.events.worker")


class EventWorkerRunResult(BaseModel):
    """Structured result of one asynchronous Knowledge submission."""

    batch_id: str = ""
    attempted_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    event_ids: list[str] = Field(default_factory=list)
    accepted: bool = False


class KnowbaseEventWorker:
    """Drain ready backlog events by handing one batch to the knowledge layer."""

    def __init__(
        self,
        *,
        backlog_service: KnowbaseEventBacklogService,
        knowledge_service: KnowledgeBatchNotificationPort,
    ):
        self._backlog_service = backlog_service
        self._knowledge_service = knowledge_service

    async def run_once(
        self,
        *,
        partition: str = "",
        limit: int = 200,
        trigger_source: str = "manual",
    ) -> EventWorkerRunResult:
        logger.info(
            "Starting backlog drain cycle.",
            extra={"partition": partition, "limit": limit, "trigger_source": trigger_source},
        )
        batch = self._backlog_service.assemble_batch(partition=partition, trigger_source=trigger_source, limit=limit)
        if batch is None:
            logger.info(
                "Backlog drain cycle found no ready events.",
                extra={"partition": partition, "limit": limit, "trigger_source": trigger_source},
            )
            return EventWorkerRunResult()
        logger.info(
                "Assembled backlog batch for Knowledge.",
            extra={
                "batch_id": batch.batch_id,
                "partition": batch.partition,
                "event_count": batch.event_count,
                "event_ids": batch.event_ids,
                "trigger_source": batch.trigger_source,
            },
        )
        self._backlog_service.mark_batch_running(event_ids=batch.event_ids)
        await self._knowledge_service.notify_batch(batch=batch)
        return EventWorkerRunResult(
            batch_id=batch.batch_id,
            attempted_count=batch.event_count,
            completed_count=0,
            failed_count=0,
            event_ids=batch.event_ids,
            accepted=True,
        )
