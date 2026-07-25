"""Knowledge-facing facade for partition statistics."""

from __future__ import annotations

from internal.knowledge.statistics.models import (
    CaseObservation,
    CaseSupportQuery,
    QueryObservation,
    SemanticObservation,
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

    def append_case_observation(self, *, observation: CaseObservation) -> StatisticsSnapshot:
        return self._writer.append_case_observation(observation=observation)

    def replace_case_observation(
        self,
        *,
        old_observation: CaseObservation,
        new_observation: CaseObservation,
    ) -> StatisticsSnapshot:
        return self._writer.replace_case_observation(
            old_observation=old_observation,
            new_observation=new_observation,
        )

    def remove_observation(self, *, observation: SemanticObservation) -> StatisticsSnapshot | None:
        return self._writer.remove_observation(observation=observation)

    def load_partition_statistics(self, *, partition: str) -> StatisticsSnapshot | None:
        return self._reader.load_partition_statistics(partition=partition)

    def stamp_source_revision(self, *, partition: str, source_revision: str) -> StatisticsSnapshot | None:
        with self._store.lock(partition=partition):
            snapshot = self._store.load(partition=partition)
            if snapshot is None:
                return None
            updated = snapshot.model_copy(update={"source_revision": source_revision})
            self._store.save(statistics=updated)
            return updated

    def query_key_stats(
        self,
        *,
        partition: str,
        source: StatisticsSource = "case",
    ) -> dict[str, int]:
        if source == "query":
            raise ValueError("query statistics are owned by QueryStatisticsService")
        return self._reader.query_key_stats(partition=partition, source=source)

    def find_supporting_cases(self, *, partition: str, query: CaseSupportQuery) -> list[str]:
        return self._reader.find_supporting_cases(partition=partition, query=query)

    def rebuild_partition_statistics(
        self,
        *,
        partition: str,
        observations: list[SemanticObservation],
    ) -> StatisticsSnapshot:
        return self._writer.rebuild_partition_statistics(
            partition=partition,
            observations=observations,
        )


class QueryStatisticsService:
    """Record runtime query signals outside the knowledge Git snapshot."""

    def __init__(self, *, writer: StatisticsWriter, reader: StatisticsReader) -> None:
        self._writer = writer
        self._reader = reader

    def record(self, *, observation: QueryObservation) -> StatisticsSnapshot:
        return self._writer.append_query_observation(observation=observation)

    def load_partition_statistics(self, *, partition: str) -> StatisticsSnapshot | None:
        return self._reader.load_partition_statistics(partition=partition)


__all__ = ["KnowledgeStatisticsService", "QueryStatisticsService"]
