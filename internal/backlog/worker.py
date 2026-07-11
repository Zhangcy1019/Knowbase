"""Worker helpers for draining persisted backlog batches."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel, Field

from internal.ports import BacklogDispatchPort, RuntimeHarnessPort
from internal.runtime.contracts import RuntimeRunResult
from internal.utils.logger import get_logger

from .queue import KnowbaseEventBacklogService


logger = get_logger("knowbase.events.worker")


class EventWorkerRunResult(BaseModel):
    """Structured result of one backlog drain cycle."""

    batch_id: str = ""
    attempted_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    event_ids: list[str] = Field(default_factory=list)
    runtime_result: RuntimeRunResult | None = None


class KnowbaseEventWorker:
    """Drain ready backlog events by assembling one runtime request."""

    def __init__(
        self,
        *,
        backlog_service: KnowbaseEventBacklogService,
        dispatch_service: BacklogDispatchPort,
        runtime_service: RuntimeHarnessPort,
    ):
        self._backlog_service = backlog_service
        self._dispatch_service = dispatch_service
        self._runtime_service = runtime_service

    async def run_once(self, *, partition: str = "", limit: int = 200, trigger_source: str = "manual") -> EventWorkerRunResult:
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
            "Assembled backlog batch for runtime.",
            extra={
                "batch_id": batch.batch_id,
                "partition": batch.partition,
                "event_count": batch.event_count,
                "event_ids": batch.event_ids,
                "trigger_source": batch.trigger_source,
            },
        )
        self._backlog_service.mark_batch_running(event_ids=batch.event_ids)
        request = self._dispatch_service.build_runtime_request(batch=batch)
        runtime_result = await self._runtime_service.run_request(request=request)
        run_failed = runtime_result.status == "failed" or not runtime_result.run_id
        if run_failed:
            failed_skill_results = [item for item in runtime_result.skill_results if not item.ok]
            logger.warning(
                "Backlog batch runtime failed.",
                extra={
                    "batch_id": batch.batch_id,
                    "partition": batch.partition,
                    "event_count": batch.event_count,
                    "run_id": runtime_result.run_id,
                    "failed_skills": [
                        {
                            "skill_id": item.skill_id,
                            "invocation_id": item.invocation_id,
                            "error_message": item.error_message,
                        }
                        for item in failed_skill_results
                    ],
                    "reasoning_summary": runtime_result.reasoning_summary,
                    "final_summary": runtime_result.final_summary,
                },
            )
            self._backlog_service.fail_batch(
                event_ids=batch.event_ids,
                error_message="runtime failed or did not materialize a backlog run",
                next_retry_at=(batch.assembled_at + timedelta(minutes=15)) if batch.assembled_at else None,
                last_run_at=batch.assembled_at,
            )
            return EventWorkerRunResult(
                batch_id=batch.batch_id,
                attempted_count=batch.event_count,
                completed_count=0,
                failed_count=batch.event_count,
                event_ids=batch.event_ids,
                runtime_result=runtime_result,
            )
        logger.info(
            "Backlog batch runtime completed.",
            extra={
                "batch_id": batch.batch_id,
                "partition": batch.partition,
                "event_count": batch.event_count,
                "run_id": runtime_result.run_id,
                "run_status": runtime_result.status,
            },
        )
        self._backlog_service.complete_batch(
            event_ids=batch.event_ids,
            run_id=runtime_result.run_id,
            last_run_at=batch.assembled_at,
        )
        return EventWorkerRunResult(
            batch_id=batch.batch_id,
            attempted_count=batch.event_count,
            completed_count=batch.event_count,
            failed_count=0,
            event_ids=batch.event_ids,
            runtime_result=runtime_result,
        )
