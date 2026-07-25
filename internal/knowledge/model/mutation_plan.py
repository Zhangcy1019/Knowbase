"""Immutable input for applying an accepted Knowledge maintenance decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from internal.knowledge.projection.models import CaseProjectionChange, ProjectionPlan


@dataclass(slots=True)
class KnowledgeMutationPlan:
    """Combine one accepted schema decision with its deterministic case projections."""

    plan_id: str
    batch_id: str
    partition: str
    created_at: str
    risk_level: str = "medium"
    accepted_schema: object | None = None
    case_changes: list[CaseProjectionChange] = field(default_factory=list)
    affected_case_ids: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def from_governance(
        cls,
        *,
        batch,
        governance,
        projection: ProjectionPlan | None,
    ) -> "KnowledgeMutationPlan":
        changes = list(projection.changes) if projection is not None else []
        partition = getattr(batch, "partition", "") or getattr(batch, "partition_name", "")
        return cls(
            plan_id=f"mutation-{uuid4().hex}",
            batch_id=getattr(batch, "batch_id", ""),
            partition=partition,
            created_at=datetime.now(timezone.utc).isoformat(),
            risk_level=getattr(governance, "risk_level", "medium"),
            accepted_schema=(
                getattr(governance, "accepted_schema", None)
                if cls._has_schema_change(governance)
                else None
            ),
            case_changes=changes,
            affected_case_ids=[change.case_id for change in changes],
            reasons=list(getattr(governance, "reasons", [])),
            summary=f"Apply {len(changes)} case facet change(s) in partition {partition}.",
        )

    @staticmethod
    def _has_schema_change(governance) -> bool:
        proposal = getattr(governance, "proposal", None)
        if proposal is None:
            return False
        return any(
            getattr(proposal, field_name, [])
            for field_name in (
                "suggested_new_keys",
                "suggested_updated_keys",
                "suggested_removed_keys",
            )
        )


__all__ = ["KnowledgeMutationPlan"]
