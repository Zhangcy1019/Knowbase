"""Knowledge-owned batch handling and runtime orchestration."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from internal.ports import KnowledgeBatchNotificationPort
from internal.ports import EventBacklogPort
from typing import Any

from internal.ports.backlog import PartitionTaskQueuePort
from internal.utils.logger import get_logger


logger = get_logger("knowbase.knowledge.service")


class KnowbaseKnowledgeService(KnowledgeBatchNotificationPort):
    """Unified Knowledge entry service for batch and manual triggers.

    Knowledge may invoke runtime once or multiple times. Callers only submit
    work; they do not build runtime requests or observe execution details.
    """

    def __init__(
        self,
        *,
        backlog_service: EventBacklogPort,
        workflow,
        task_queue: PartitionTaskQueuePort | None = None,
    ):
        self._backlog_service = backlog_service
        self._workflow = workflow
        if task_queue is None:
            raise ValueError("KnowbaseKnowledgeService requires a partition task queue")
        self._task_queue = task_queue

    async def notify_batch(self, *, batch) -> None:
        """Accept a batch and schedule Knowledge processing in the background."""
        await self.submit_batch(batch=batch)

    async def submit_batch(self, *, batch) -> None:
        """Submit a backlog-derived batch for asynchronous processing."""
        self._task_queue.enqueue(
            partition=batch.partition,
            kind="knowledge_drain",
            payload={"batch_id": batch.batch_id, "event_ids": batch.event_ids},
            handler=lambda task: self._process_batch_task(task=task, batch=batch),
        )
        logger.info(
            "Knowledge batch accepted for asynchronous processing.",
            extra={"batch_id": batch.batch_id, "partition": batch.partition},
        )

    async def submit_manual(self, *, batch) -> None:
        """Submit a manually triggered Knowledge batch asynchronously."""
        self._task_queue.enqueue(
            partition=batch.partition,
            kind="knowledge_drain",
            payload={"batch_id": batch.batch_id, "trigger": "manual"},
            handler=lambda task: self._process_request_task(task=task, batch=batch),
        )

    async def wait_partition_idle(self, *, partition: str) -> None:
        """Test/worker hook to await all queued work for one partition."""
        await self._task_queue.wait_idle(partition=partition)

    async def _process_batch_task(self, *, task: Any, batch) -> None:
        await self._process_batch(batch)

    async def _process_request_task(self, *, task: Any, batch) -> None:
        await self._process_request(batch=batch)

    async def _process_request(self, *, batch) -> None:
        try:
            await self._workflow.run_manual(batch=batch)
        except Exception:
            logger.exception(
                "Manual Knowledge request crashed.",
                extra={"batch_id": batch.batch_id},
            )

    async def _process_batch(self, batch) -> None:
        try:
            workflow_result = await self._workflow.run_batch(batch=batch)
            if workflow_result.status != "completed":
                logger.warning(
                    "Knowledge batch did not complete.",
                    extra={"batch_id": batch.batch_id, "mutation_plan_id": workflow_result.mutation_plan_id},
                )
                self._backlog_service.fail_batch(
                    event_ids=batch.event_ids,
                    error_message=workflow_result.error_message or "knowledge processing did not complete",
                    next_retry_at=(batch.assembled_at + timedelta(minutes=15)) if batch.assembled_at else None,
                    last_run_at=batch.assembled_at,
                )
                return
            self._backlog_service.complete_batch(
                event_ids=batch.event_ids,
                run_id=workflow_result.committed_revision or workflow_result.mutation_plan_id,
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
