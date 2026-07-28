"""Decision state transitions and review lock coordination."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.knowledge.decision.models import (
    KnowledgeDecisionExecution,
    KnowledgeDecisionRecord,
    KnowledgeDecisionStage,
    KnowledgeDecisionStatus,
    KnowledgeDecisionTransition,
)
from internal.knowledge.decision.repository import KnowledgeDecisionRepository
from internal.knowledge.decision.review_lock import PartitionReviewBlockedError, PartitionReviewLock


class KnowledgeDecisionService:
    """Persist decisions and enforce their review lifecycle."""

    def __init__(self, *, repository: KnowledgeDecisionRepository, review_lock: PartitionReviewLock):
        self._repository = repository
        self._review_lock = review_lock

    def create(self, record: KnowledgeDecisionRecord) -> KnowledgeDecisionRecord:
        # if record.status == "requires_review", acquire a review lock for the partition
        if record.status == "requires_review":
            self._review_lock.acquire(partition=record.partition, decision_id=record.decision_id)
        
        # if the record has no status history, initialize it with the current status
        if not record.status_history:
            record = record.model_copy(update={
                "status_history": [
                    KnowledgeDecisionTransition(to_status=record.status),
                ],
            })
        return self._repository.save(record)

    def get(self, decision_id: str) -> KnowledgeDecisionRecord | None:
        return self._repository.get(decision_id)

    def ensure_partition_available(self, *, partition: str) -> None:
        """Fail before expensive governance work when review freezes a partition."""
        existing = self._review_lock.get(partition=partition)
        if existing is not None:
            raise PartitionReviewBlockedError(
                partition=partition,
                decision_id=str(existing.get("decision_id") or "unknown"),
            )

    def list(
        self,
        *,
        partition: str = "",
        status: str = "",
    ) -> list[KnowledgeDecisionRecord]:
        """List persisted decisions for Knowledge inspection surfaces."""
        return self._repository.list(partition=partition, status=status)

    def transition(
        self,
        *,
        decision_id: str,
        status: KnowledgeDecisionStatus,
        reviewer: str = "",
        reason: str = "",
        error_message: str = "",
        applied_revision: str = "",
        execution: dict | None = None,
        stages: dict[str, KnowledgeDecisionStage] | None = None,
        actor: str = "",
    ) -> KnowledgeDecisionRecord:
        current = self._repository.get(decision_id)
        if current is None:
            raise ValueError(f"decision not found: {decision_id}")
        if not self._allowed(current.status, status):
            raise ValueError(f"invalid decision transition: {current.status} -> {status}")
        updated = current.model_copy(
            update={
                "status": status,
                "reviewer": reviewer or current.reviewer,
                "review_reason": reason or current.review_reason,
                "stages": {**current.stages, **(stages or {})},
                "execution": (
                    KnowledgeDecisionExecution.model_validate(execution)
                    if execution is not None
                    else current.execution
                ),
                "status_history": [
                    *current.status_history,
                    KnowledgeDecisionTransition(
                        from_status=current.status,
                        to_status=status,
                        reason=reason or None,
                        error=error_message or None,
                        actor=actor or None,
                    ),
                ],
                "updated_at": datetime.now(timezone.utc),
            }
        )
        if applied_revision:
            next_execution = updated.execution or KnowledgeDecisionExecution()
            updated = updated.model_copy(update={
                "execution": next_execution.model_copy(update={"applied_revision": applied_revision}),
            })
        if status == "requires_review":
            self._review_lock.acquire(partition=current.partition, decision_id=decision_id)
        elif status in {"no_change", "approved", "discarded", "retry_requested", "stale", "applied", "failed", "rolled_back", "partition_deleted"}:
            self._review_lock.release(partition=current.partition, decision_id=decision_id)
        return self._repository.save(updated)

    @staticmethod
    def _allowed(current: str, target: str) -> bool:
        allowed = {
            "accepted": {"applying", "stale", "failed"},
            "applying": {"applied", "failed", "rolled_back"},
            "requires_review": {"accepted", "approved", "discarded", "retry_requested", "stale", "partition_deleted"},
            "approved": {"applying", "stale", "failed"},
            "applied": {"rolled_back", "failed"},
        }
        return target in allowed.get(current, set())


__all__ = ["KnowledgeDecisionService"]
