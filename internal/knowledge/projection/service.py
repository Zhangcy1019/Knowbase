"""Case projection capability facade."""

from __future__ import annotations


class KnowledgeProjectionService:
    """Plan case facet changes without applying them directly."""

    def plan(self, *, schema_change, case_ids: list[str]):
        raise NotImplementedError

