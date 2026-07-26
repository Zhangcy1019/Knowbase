"""Contracts for asynchronous partition operations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


PartitionTaskKind = Literal[
    "case_input",
    "case_update",
    "case_delete",
    "knowledge_drain",
    "review_apply",
    "partition_disable",
    "partition_delete",
]
PartitionTaskStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class PartitionTask(BaseModel):
    """One command executed serially within a partition."""

    task_id: str = Field(default_factory=lambda: f"task-{uuid4().hex}")
    partition: str
    kind: PartitionTaskKind
    payload: dict[str, Any] = Field(default_factory=dict)
    status: PartitionTaskStatus = "queued"
    attempt_count: int = 0
    error_message: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None


__all__ = ["PartitionTask", "PartitionTaskKind", "PartitionTaskStatus"]
