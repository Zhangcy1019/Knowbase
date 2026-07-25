"""Knowledge-facing facade for partition statistics."""

from __future__ import annotations

from internal.knowledge.statistics.models import (
    CaseObservation,
    CaseSupportQuery,
    QueryObservation,
    StatisticsSnapshot,
    StatisticsSource,
)
from internal.knowledge.statistics.reader import StatisticsReader
from internal.knowledge.statistics.store import StatisticsStore
from internal.knowledge.statistics.writer import StatisticsWriter


class KnowledgeStatisticsService:
    """Compose observation writing, reading, and snapshot persistence."""

    def __init__(self, *, reader: StatisticsReader, writer: StatisticsWriter, store: StatisticsStore) -> None:
        self._reader = reader
        self._writer = writer
        self._store = store

    def append_case_observation(self, *, observation: CaseObservation) -> None:
        self._writer.append_case_observation(observation=observation)

    def append_query_observation(self, *, observation: QueryObservation) -> None:
        self._writer.append_query_observation(observation=observation)

    def load_partition_statistics(self, *, partition: str) -> StatisticsSnapshot | None:
        return self._reader.load_partition_statistics(partition=partition)

    def query_key_stats(
        self,
        *,
        partition: str,
        source: StatisticsSource = "case",
    ) -> dict[str, int]:
        return self._reader.query_key_stats(partition=partition, source=source)

    def find_supporting_cases(self, *, partition: str, query: CaseSupportQuery) -> list[str]:
        return self._reader.find_supporting_cases(partition=partition, query=query)

    def rebuild_partition_statistics(self, *, partition: str) -> StatisticsSnapshot:
        statistics = self._writer.rebuild_partition_statistics(partition=partition)
        self._store.save(statistics=statistics)
        return statistics


__all__ = ["KnowledgeStatisticsService"]
