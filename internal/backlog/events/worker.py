"""Worker for submitting event batches to Knowledge."""

from pydantic import BaseModel, Field

from internal.ports import KnowledgeBatchNotificationPort
from internal.utils.logger import get_logger

from internal.backlog.events.queue import KnowbaseEventBacklogService


logger = get_logger("knowbase.events.worker")


class EventWorkerRunResult(BaseModel):
    batch_id: str = ""
    attempted_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    event_ids: list[str] = Field(default_factory=list)
    accepted: bool = False


class KnowbaseEventWorker:
    def __init__(self, *, backlog_service: KnowbaseEventBacklogService, knowledge_service: KnowledgeBatchNotificationPort):
        self._backlog_service = backlog_service
        self._knowledge_service = knowledge_service

    async def run_once(self, *, partition: str = "", limit: int = 200, trigger_source: str = "manual") -> EventWorkerRunResult:
        logger.info("Starting backlog drain cycle.", extra={"partition": partition, "limit": limit, "trigger_source": trigger_source})
        batch = self._backlog_service.assemble_batch(partition=partition, trigger_source=trigger_source, limit=limit)
        if batch is None:
            return EventWorkerRunResult()
        self._backlog_service.mark_batch_running(event_ids=batch.event_ids)
        await self._knowledge_service.notify_batch(batch=batch)
        return EventWorkerRunResult(batch_id=batch.batch_id, attempted_count=batch.event_count, event_ids=batch.event_ids, accepted=True)


__all__ = ["EventWorkerRunResult", "KnowbaseEventWorker"]
