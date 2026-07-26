"""In-process FIFO scheduling for partition tasks."""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone

from internal.backlog.tasks.models import PartitionTask, PartitionTaskKind


TaskHandler = Callable[[PartitionTask], Awaitable[None]]


class PartitionTaskQueue:
    """Serialize asynchronous commands independently for each partition.

    This is deliberately not a durable queue yet. Cross-process safety for
    actual file/Git mutations is provided by the infrastructure coordination
    lock used by the handler.
    """

    def __init__(self) -> None:
        self._queues: dict[str, deque[tuple[PartitionTask, TaskHandler]]] = {}
        self._workers: dict[str, asyncio.Task[None]] = {}
        self._tasks: dict[str, PartitionTask] = {}

    def enqueue(
        self,
        *,
        partition: str,
        kind: PartitionTaskKind,
        handler: TaskHandler,
        payload: dict | None = None,
    ) -> PartitionTask:
        task = PartitionTask(partition=partition, kind=kind, payload=payload or {})
        self._tasks[task.task_id] = task
        queue = self._queues.setdefault(partition, deque())
        queue.append((task, handler))
        if partition not in self._workers or self._workers[partition].done():
            self._workers[partition] = asyncio.create_task(
                self._drain(partition),
                name=f"backlog:partition:{partition}",
            )
        return task

    def get(self, task_id: str) -> PartitionTask | None:
        """Return the current in-process state for a submitted task."""
        return self._tasks.get(task_id)

    async def wait_idle(self, *, partition: str) -> None:
        worker = self._workers.get(partition)
        if worker is not None:
            await worker

    async def _drain(self, partition: str) -> None:
        queue = self._queues[partition]
        while queue:
            task, handler = queue.popleft()
            task.status = "running"
            task.attempt_count += 1
            task.started_at = datetime.now(timezone.utc)
            try:
                await handler(task)
            except Exception as exc:  # pragma: no cover - handler owns logging
                task.status = "failed"
                task.error_message = str(exc)
            else:
                task.status = "completed"
            finally:
                task.finished_at = datetime.now(timezone.utc)
        self._queues.pop(partition, None)
        self._workers.pop(partition, None)


__all__ = ["PartitionTaskQueue", "TaskHandler"]
