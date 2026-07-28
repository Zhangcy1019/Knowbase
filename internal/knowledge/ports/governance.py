"""Internal port for facet schema analysis."""

from __future__ import annotations

from typing import Any, Protocol

from internal.knowledge.governance.contracts import GovernanceStatisticsInput
from internal.knowledge.governance.models import GovernanceResult
from internal.models.facet import PartitionFacetSchema


class KnowledgeGovernancePort(Protocol):
    """Analyze and evaluate facet-schema governance decisions."""

    def assess_deterministic(
        self,
        *,
        statistics: GovernanceStatisticsInput,
        current_schema: PartitionFacetSchema,
        working_set: Any,
    ) -> GovernanceResult:
        ...

    async def assess_async(
        self,
        *,
        statistics: GovernanceStatisticsInput,
        current_schema: PartitionFacetSchema,
        working_set: Any,
    ) -> GovernanceResult:
        ...


__all__ = ["KnowledgeGovernancePort"]
