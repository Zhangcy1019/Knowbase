"""Internal port for the top-level Knowledge workflow."""

from __future__ import annotations

from typing import Any, Protocol

from internal.knowledge.workflow.result import KnowledgeWorkflowResult

class KnowledgeDrainPort(Protocol):
    """Execute one Knowledge drain or manually triggered maintenance task."""

    async def run_batch(self, *, batch: Any) -> KnowledgeWorkflowResult:
        ...

    async def run_manual(self, *, batch: Any) -> KnowledgeWorkflowResult:
        ...


__all__ = ["KnowledgeDrainPort"]
