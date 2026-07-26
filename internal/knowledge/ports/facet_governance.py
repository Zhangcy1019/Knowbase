"""Internal port for facet schema analysis."""

from __future__ import annotations

from typing import Any, Protocol

from internal.knowledge.facet_governance.models import FacetGovernanceResult


class KnowledgeFacetGovernancePort(Protocol):
    """Analyze and evaluate facet-schema governance decisions."""

    def assess(self, *, statistics: Any, current_schema: Any, working_set: Any) -> FacetGovernanceResult:
        ...


__all__ = ["KnowledgeFacetGovernancePort"]
