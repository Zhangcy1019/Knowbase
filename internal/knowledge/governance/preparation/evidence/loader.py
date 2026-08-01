"""Load the read-only resources needed by governance."""

from __future__ import annotations

from dataclasses import dataclass

from internal.knowledge.batch.models import BatchWorkingSet
from internal.models import KnowbaseCaseDocument
from internal.models.facet import PartitionFacetIndex
from internal.models.partition_semantic_index import PartitionSemanticIndex
from internal.knowledge.statistics.models import CaseStatisticsSnapshot
from internal.ports import CaseReadPort, PartitionProfileReadPort, PartitionReadPort


@dataclass(slots=True)
class GovernanceEvidenceInputs:
    """Raw resources loaded for one governance assessment."""

    partition_status: str
    partition_scenario_description: str
    enabled_facet_keys: list[str]
    affected_cases: list[KnowbaseCaseDocument]
    facet_index: PartitionFacetIndex | None
    semantic_index: PartitionSemanticIndex | None
    statistics_snapshot: CaseStatisticsSnapshot | None


class GovernanceEvidenceLoader:
    """Read partition, case, schema, and index state without deciding anything."""

    def __init__(
        self,
        *,
        partition_service: PartitionReadPort | PartitionProfileReadPort,
        case_repository: CaseReadPort,
    ):
        self._partition_service = partition_service
        self._case_repository = case_repository

    def load(
        self,
        *,
        batch_working_set: BatchWorkingSet,
        statistics: CaseStatisticsSnapshot | None = None,
    ) -> GovernanceEvidenceInputs:
        partition = self._partition_service.get_partition(batch_working_set.partition)
        facet_schema = self._partition_service.get_facet_schema(batch_working_set.partition)
        definitions = [] if facet_schema is None else [item for item in facet_schema.definitions if item.enabled]
        enabled_facet_keys = [item.key for item in definitions if item.key.strip()]
        affected_cases = self._case_repository.get_many(list(dict.fromkeys(batch_working_set.affected_case_ids)))
        return GovernanceEvidenceInputs(
            partition_status="missing" if partition is None else partition.status,
            partition_scenario_description="" if partition is None else partition.scenario_description,
            enabled_facet_keys=enabled_facet_keys,
            affected_cases=affected_cases,
            facet_index=self._partition_service.get_facet_index(batch_working_set.partition),
            semantic_index=self._partition_service.get_semantic_index(batch_working_set.partition),
            statistics_snapshot=statistics,
        )


__all__ = ["GovernanceEvidenceInputs", "GovernanceEvidenceLoader"]
