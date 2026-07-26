"""Decision state transitions and review lock coordination."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.knowledge.decision.models import KnowledgeDecisionRecord, KnowledgeDecisionStatus
from internal.knowledge.decision.repository import KnowledgeDecisionRepository
from internal.knowledge.decision.review_lock import PartitionReviewLock


class KnowledgeDecisionService:
    """Persist decisions and enforce their review lifecycle."""

    def __init__(self, *, repository: KnowledgeDecisionRepository, review_lock: PartitionReviewLock):
        self._repository = repository
        self._review_lock = review_lock

    def create(self, record: KnowledgeDecisionRecord) -> KnowledgeDecisionRecord:
        if record.status == "requires_review":
            self._review_lock.acquire(partition=record.partition, decision_id=record.decision_id)
        return self._repository.save(record)

    def get(self, decision_id: str) -> KnowledgeDecisionRecord | None:
        return self._repository.get(decision_id)

    def transition(
        self,
        *,
        decision_id: str,
        status: KnowledgeDecisionStatus,
        reviewer: str = "",
        reason: str = "",
        error_message: str = "",
        applied_revision: str = "",
        mutation_plan: dict | None = None,
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
                "error_message": error_message,
                "applied_revision": applied_revision or current.applied_revision,
                "mutation_plan": mutation_plan if mutation_plan is not None else current.mutation_plan,
                "updated_at": datetime.now(timezone.utc),
            }
        )
        if status == "requires_review":
            self._review_lock.acquire(partition=current.partition, decision_id=decision_id)
        elif status in {"no_change", "discarded", "retry_requested", "stale", "applied", "failed", "rolled_back", "partition_deleted"}:
            self._review_lock.release(partition=current.partition, decision_id=decision_id)
        return self._repository.save(updated)

    @staticmethod
    def _allowed(current: str, target: str) -> bool:
        allowed = {
            "proposed": {"no_change", "accepted", "requires_review", "failed"},
            "accepted": {"approved", "applied", "stale", "failed"},
            "requires_review": {"approved", "discarded", "retry_requested", "stale", "partition_deleted"},
            "approved": {"applied", "stale", "failed", "rolled_back"},
            "applied": {"rolled_back", "failed"},
        }
        return target in allowed.get(current, set())


__all__ = ["KnowledgeDecisionService"]
