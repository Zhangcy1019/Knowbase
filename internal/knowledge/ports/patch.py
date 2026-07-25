"""Internal ports for Knowledge patch planning and execution."""

from __future__ import annotations

from typing import Any, Protocol


class KnowledgePatchBuilderPort(Protocol):
    """Build a reversible Knowledge patch from planned changes."""

    def build(self, *, schema_change: Any, projection_change: Any, batch: Any) -> Any:
        ...


class KnowledgePatchExecutorPort(Protocol):
    """Apply or roll back an already-built Knowledge patch."""

    def apply(self, *, patch: Any) -> Any:
        ...

    def rollback(self, *, patch: Any) -> None:
        ...


__all__ = ["KnowledgePatchBuilderPort", "KnowledgePatchExecutorPort"]
