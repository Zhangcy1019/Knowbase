"""Results owned by the Knowledge workflow."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class KnowledgeWorkflowResult:
    """Knowledge-level result, independent from one runtime invocation."""

    batch_id: str = ""
    status: str = "failed"
    iteration: int = 0
    runtime_run_ids: list[str] = field(default_factory=list)
    patch_id: str = ""
    schema_changed: bool = False
    requires_review: bool = False
    error_message: str = ""


__all__ = ["KnowledgeWorkflowResult"]
