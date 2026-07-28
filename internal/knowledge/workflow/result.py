"""Results owned by the Knowledge workflow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class KnowledgeWorkflowResult:
    """Knowledge-level result, independent from one runtime invocation."""

    batch_id: str = ""
    status: str = "failed"
    iteration: int = 0
    mutation_plan_id: str = ""
    decision_id: str = ""
    committed_revision: str = ""
    schema_changed: bool = False
    applied_case_ids: list[str] = field(default_factory=list)
    requires_review: bool = False
    error_message: str = ""
    mutation_kind: str = "none"
    projection_status: str = "not_run"
    apply_status: str = "not_run"


__all__ = ["KnowledgeWorkflowResult"]
