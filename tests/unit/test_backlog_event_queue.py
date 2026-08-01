"""Backlog event state transition tests.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.unit.test_backlog_event_queue
"""

import unittest
from datetime import datetime, timezone, timedelta

from internal.backlog.events.queue import KnowbaseEventBacklogService
from internal.models import EventRecord


class _Repository:
    def __init__(self, record: EventRecord):
        self.record = record

    def get(self, event_id: str):
        return self.record if self.record.event_id == event_id else None

    def save(self, record: EventRecord):
        self.record = record
        return record


class BacklogEventQueueTest(unittest.TestCase):
    def test_failed_event_can_be_requeued_without_run_id(self) -> None:
        repository = _Repository(
            EventRecord(
                event_id="event-1",
                event_type="case.created",
                partition="CI",
                payload={},
                status="failed",
                error_message="knowledge processing failed",
                attempt_count=1,
                next_retry_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            )
        )
        service = KnowbaseEventBacklogService(repository=repository)

        result = service.requeue_event(event_id="event-1")

        self.assertEqual(result.status, "pending")
        self.assertEqual(result.error_message, "")
        self.assertIsNone(result.next_retry_at)
        self.assertEqual(result.run_id, "")
        self.assertEqual(result.attempt_count, 1)


if __name__ == "__main__":
    unittest.main()
