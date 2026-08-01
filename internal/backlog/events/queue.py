"""Persisted event backlog state and batch assembly."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from internal.backlog.events.models import BacklogBatch
from internal.models import EventRecord


class KnowbaseEventBacklogService:
    """Manage persisted event state transitions and batch assembly."""

    def __init__(self, *, repository):
        self._repository = repository

    def list_events(self, *, partition: str = "", status: str = "", event_type: str = "", size: int = 500) -> list[EventRecord]:
        return self._repository.list(partition=partition, status=status, event_type=event_type, size=size)

    def get_event(self, event_id: str) -> EventRecord | None:
        return self._repository.get(event_id)

    def delete_event(self, event_id: str) -> None:
        self._repository.delete(event_id)

    def mark_ready(self, *, event_id: str) -> EventRecord:
        record = self._require_event(event_id)
        return self._repository.save(record.model_copy(update={"status": "pending", "error_message": "", "next_retry_at": None}))

    def mark_ignored(self, *, event_id: str) -> EventRecord:
        record = self._require_event(event_id)
        return self._repository.save(record.model_copy(update={"status": "completed", "error_message": ""}))

    def requeue_event(self, *, event_id: str) -> EventRecord:
        record = self._require_event(event_id)
        return self._repository.save(record.model_copy(update={"status": "pending", "run_id": "", "error_message": "", "next_retry_at": None, "updated_at": datetime.now(timezone.utc)}))

    def mark_batch_running(self, *, event_ids: list[str]) -> list[EventRecord]:
        now = datetime.now(timezone.utc)
        return [self._repository.save(self._require_event(event_id).model_copy(update={"status": "pending", "updated_at": now})) for event_id in event_ids]

    def complete_batch(self, *, event_ids: list[str], run_id: str = "", last_run_at: datetime | None = None) -> list[EventRecord]:
        now = datetime.now(timezone.utc)
        updated: list[EventRecord] = []
        for event_id in event_ids:
            record = self._require_event(event_id)
            updated.append(
                self._repository.save(
                    record.model_copy(
                        update={
                            "status": "completed",
                            "run_id": run_id or record.run_id,
                            "last_run_at": last_run_at or now,
                            "next_retry_at": None,
                            "error_message": "",
                            "updated_at": now,
                        }
                    )
                )
            )
        return updated

    def fail_batch(self, *, event_ids: list[str], error_message: str, next_retry_at: datetime | None, last_run_at: datetime | None = None) -> list[EventRecord]:
        now = datetime.now(timezone.utc)
        updated: list[EventRecord] = []
        for event_id in event_ids:
            record = self._require_event(event_id)
            updated.append(self._repository.save(record.model_copy(update={"status": "failed", "attempt_count": record.attempt_count + 1, "last_run_at": last_run_at or now, "next_retry_at": next_retry_at, "error_message": error_message, "updated_at": now})))
        return updated

    def list_ready_events(self, *, partition: str = "", limit: int = 100) -> list[EventRecord]:
        candidates = self._repository.list(partition=partition, size=max(limit * 3, 100))
        now = datetime.now(timezone.utc)
        return [item for item in candidates if item.status in {"pending", "failed"} and (item.next_retry_at is None or item.next_retry_at <= now)][:limit]

    def assemble_batch(self, *, partition: str = "", trigger_source: str = "manual", limit: int = 200) -> BacklogBatch | None:
        events = self.list_ready_events(partition=partition, limit=limit)
        if not events:
            return None
        return self._build_batch(events=events, partition=partition, trigger_source=trigger_source)

    def _require_event(self, event_id: str) -> EventRecord:
        record = self._repository.get(event_id.strip())
        if record is None:
            raise ValueError(f"event not found: {event_id}")
        return record

    @staticmethod
    def _build_batch(*, events: list[EventRecord], partition: str, trigger_source: str) -> BacklogBatch:
        assembled_at = datetime.now(timezone.utc)
        batch_partition = partition or (events[0].partition if events else "")
        event_type_counts = dict(Counter(str(item.event_type) for item in events))
        return BacklogBatch(
            batch_id=f"batch-{batch_partition or 'global'}-{int(assembled_at.timestamp() * 1000)}",
            partition=batch_partition,
            trigger_source=trigger_source,
            event_ids=[item.event_id for item in events],
            event_count=len(events),
            event_type_counts=event_type_counts,
            resource_refs=[f"{item.resource_type}:{item.resource_id}" for item in events],
            assembled_at=assembled_at,
            events=events,
            summary=f"Drain {len(events)} backlog event(s) for partition {batch_partition or 'global'}.",
            metadata={"trigger_source": trigger_source},
        )


__all__ = ["KnowbaseEventBacklogService"]
