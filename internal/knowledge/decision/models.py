"""Persistent, stage-oriented Knowledge drain audit contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


KnowledgeDecisionStatus = Literal[
    "no_change",
    "requires_review",
    "accepted",
    "approved",
    "applying",
    "applied",
    "discarded",
    "retry_requested",
    "stale",
    "rolled_back",
    "failed",
    "partition_deleted",
]

KnowledgeStageStatus = Literal[
    "completed",
    "passed",
    "no_action",
    "blocked",
    "failed",
    "not_run",
]


class KnowledgeDecisionInput(BaseModel):
    """Immutable evidence frozen before governance starts."""

    base_revision: str | None = None
    statistics_fingerprint: str | None = None
    statistics_snapshot: dict[str, Any] | None = None
    working_set: dict[str, Any] | None = None


class KnowledgeDecisionStage(BaseModel):
    """One executed stage and its bounded input/output evidence."""

    status: KnowledgeStageStatus
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    reasons: list[str] = Field(default_factory=list)
    error: str | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeDecisionOutcome(BaseModel):
    """Business conclusion produced by Governance."""

    outcome: Literal["no_change", "accepted", "requires_review", "failed"]
    accepted_schema: dict[str, Any] | None = None
    reasons: list[str] = Field(default_factory=list)
    reason_details: list[dict[str, Any]] = Field(default_factory=list)


class KnowledgeDecisionExecution(BaseModel):
    """Actual mutation and version-control result, separate from the plan."""

    plan: dict[str, Any] | None = None
    planned_paths: list[str] = Field(default_factory=list)
    changed_paths: list[str] = Field(default_factory=list)
    updated_case_ids: list[str] = Field(default_factory=list)
    applied_revision: str | None = None
    rolled_back: bool = False
    error: str | None = None
    mutation_kind: Literal["none", "schema_change", "projection_only", "schema_and_projection"] = "none"
    projection_status: Literal[
        "not_run", "completed", "no_action", "no_materialized_values", "failed"
    ] = "not_run"
    apply_status: Literal["not_run", "applied", "no_op", "blocked", "failed"] = "not_run"


class KnowledgeDecisionTransition(BaseModel):
    """One persisted status transition."""

    from_status: KnowledgeDecisionStatus | None = None
    to_status: KnowledgeDecisionStatus
    reason: str | None = None
    error: str | None = None
    actor: str | None = None
    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KnowledgeDecisionRecord(BaseModel):
    """Complete audit record for one Knowledge drain attempt."""

    decision_id: str = Field(default_factory=lambda: f"decision-{uuid4().hex}")
    runtime_run_id: str | None = None
    partition: str
    batch_id: str
    status: KnowledgeDecisionStatus
    input: KnowledgeDecisionInput
    stages: dict[str, KnowledgeDecisionStage] = Field(default_factory=dict)
    outcome: KnowledgeDecisionOutcome
    execution: KnowledgeDecisionExecution | None = None
    status_history: list[KnowledgeDecisionTransition] = Field(default_factory=list) # record of all status transitions
    reviewer: str | None = None
    review_reason: str | None = None
    supersedes_decision_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = [
    "KnowledgeDecisionExecution",
    "KnowledgeDecisionInput",
    "KnowledgeDecisionOutcome",
    "KnowledgeDecisionRecord",
    "KnowledgeDecisionStage",
    "KnowledgeDecisionStatus",
    "KnowledgeDecisionTransition",
    "KnowledgeStageStatus",
]
