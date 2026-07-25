"""Knowledge-owned batch handling and runtime orchestration."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from internal.ports import KnowledgeBatchNotificationPort
from internal.ports import EventBacklogPort
from internal.utils.logger import get_logger


logger = get_logger("knowbase.knowledge.service")


class KnowbaseKnowledgeService(KnowledgeBatchNotificationPort):
    """Unified Knowledge entry service for batch and manual triggers.

    Knowledge may invoke runtime once or multiple times. Callers only submit
    work; they do not build runtime requests or observe execution details.
    """

    def __init__(self, *, backlog_service: EventBacklogPort, workflow):
        self._backlog_service = backlog_service
        self._workflow = workflow
        self._tasks: set[asyncio.Task[None]] = set()

    async def notify_batch(self, *, batch) -> None:
        """Accept a batch and schedule Knowledge processing in the background."""
        await self.submit_batch(batch=batch)

    async def submit_batch(self, *, batch) -> None:
        """Submit a backlog-derived batch for asynchronous processing."""
        task = asyncio.create_task(self._process_batch(batch), name=f"knowledge:batch:{batch.batch_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        logger.info(
            "Knowledge batch accepted for asynchronous processing.",
            extra={"batch_id": batch.batch_id, "partition": batch.partition},
        )

    async def submit_manual(self, *, request) -> None:
        """Submit a manually triggered Knowledge request asynchronously."""
        task = asyncio.create_task(
            self._process_request(request=request),
            name=f"knowledge:manual:{getattr(request, 'request_id', 'request')}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _process_request(self, *, request) -> None:
        try:
            await self._workflow.run_manual(request=request)
        except Exception:
            logger.exception(
                "Manual Knowledge request crashed.",
                extra={"request_id": getattr(request, "request_id", "")},
            )

    async def _process_batch(self, batch) -> None:
        try:
            workflow_result = await self._workflow.run_batch(batch=batch)
            if workflow_result.status == "failed" or not workflow_result.runtime_run_ids:
                logger.warning(
                    "Knowledge batch runtime failed.",
                    extra={"batch_id": batch.batch_id, "run_ids": workflow_result.runtime_run_ids},
                )
                self._backlog_service.fail_batch(
                    event_ids=batch.event_ids,
                    error_message="knowledge runtime failed or did not materialize a run",
                    next_retry_at=(batch.assembled_at + timedelta(minutes=15)) if batch.assembled_at else None,
                    last_run_at=batch.assembled_at,
                )
                return
            self._backlog_service.complete_batch(
                event_ids=batch.event_ids,
                run_id=workflow_result.runtime_run_ids[-1],
                last_run_at=batch.assembled_at,
            )
        except Exception as exc:
            logger.exception("Knowledge batch processing crashed.", extra={"batch_id": batch.batch_id})
            self._backlog_service.fail_batch(
                event_ids=batch.event_ids,
                error_message=f"knowledge processing crashed: {exc}",
                next_retry_at=(batch.assembled_at + timedelta(minutes=15)) if batch.assembled_at else None,
                last_run_at=batch.assembled_at,
            )


__all__ = ["KnowbaseKnowledgeService"]
