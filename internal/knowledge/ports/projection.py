"""Internal port for case facet projection planning."""

from __future__ import annotations

from typing import Any, Protocol


class KnowledgeProjectionPort(Protocol):
    """Plan case projections under an accepted schema."""

    def plan(self, *, partition: str, accepted_schema: Any, case_ids: list[str]) -> Any:
        ...


__all__ = ["KnowledgeProjectionPort"]
