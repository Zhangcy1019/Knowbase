"""Persistent Knowledge decision and review contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


KnowledgeDecisionStatus = Literal[
    "proposed",
    "no_change",
    "accepted",
    "requires_review",
    "approved",
    "applied",
    "discarded",
    "retry_requested",
    "stale",
    "rolled_back",
    "failed",
    "partition_deleted",
]


class KnowledgeDecisionRecord(BaseModel):
    """Immutable-input audit record for one Knowledge governance attempt."""

    decision_id: str = Field(default_factory=lambda: f"decision-{uuid4().hex}")
    partition: str
    batch_id: str
    status: KnowledgeDecisionStatus = "proposed"
    base_revision: str = ""
    statistics_fingerprint: str = ""
    statistics_snapshot: dict[str, Any] = Field(default_factory=dict)
    working_set_snapshot: dict[str, Any] = Field(default_factory=dict)
    governance_result: dict[str, Any] = Field(default_factory=dict)
    mutation_plan: dict[str, Any] | None = None
    applied_revision: str = ""
    reviewer: str = ""
    review_reason: str = ""
    error_message: str = ""
    supersedes_decision_id: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = ["KnowledgeDecisionRecord", "KnowledgeDecisionStatus"]
