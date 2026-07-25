"""Statistics read/write/store ports owned by Knowledge."""

from __future__ import annotations

from typing import Protocol

from internal.knowledge.statistics.models import (
    CaseObservation,
    CaseSupportQuery,
    QueryObservation,
    SemanticObservation,
    CaseStatisticsSnapshot,
    QueryStatisticsSnapshot,
    StatisticsSource,
)


class KnowledgeStatisticsReaderPort(Protocol):
    """Read partition statistics and support indexes."""

    def load_partition_statistics(self, *, partition: str) -> CaseStatisticsSnapshot | None:
        ...

    def query_key_stats(
        self,
        *,
        partition: str,
        source: StatisticsSource = "case",
    ) -> dict[str, int]:
        ...

    def find_supporting_cases(self, *, partition: str, query: CaseSupportQuery) -> list[str]:
        ...


class KnowledgeStatisticsWriterPort(Protocol):
    """Accept structured case/query observations for aggregation."""

    def append_case_observation(self, *, observation: CaseObservation) -> CaseStatisticsSnapshot:
        ...

    def rebuild_partition_statistics(
        self,
        *,
        partition: str,
        observations: list[SemanticObservation],
    ) -> CaseStatisticsSnapshot:
        ...


class QueryStatisticsPort(Protocol):
    """Record runtime query signals outside knowledge statistics."""

    def record(self, *, observation: QueryObservation) -> QueryStatisticsSnapshot:
        ...


class KnowledgeStatisticsStorePort(Protocol):
    """Persist and load complete statistics snapshots."""

    def load(self, *, partition: str) -> CaseStatisticsSnapshot | QueryStatisticsSnapshot | None:
        ...

    def save(self, *, statistics: CaseStatisticsSnapshot | QueryStatisticsSnapshot) -> None:
        ...


__all__ = [
    "KnowledgeStatisticsReaderPort",
    "KnowledgeStatisticsStorePort",
    "KnowledgeStatisticsWriterPort",
    "QueryStatisticsPort",
]
