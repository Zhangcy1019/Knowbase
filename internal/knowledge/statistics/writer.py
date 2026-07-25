"""Incremental and full statistics update capability."""

from __future__ import annotations

from internal.knowledge.statistics.models import (
    CaseObservation,
    QueryObservation,
    SemanticObservation,
    StatisticsSnapshot,
)


class StatisticsWriter:
    """Update the current snapshot; observation storage remains external."""

    def __init__(self, *, snapshot_store, normalizer, aggregator) -> None:
        self._snapshot_store = snapshot_store
        self._normalizer = normalizer
        self._aggregator = aggregator

    def append_case_observation(self, *, observation: CaseObservation) -> StatisticsSnapshot:
        return self._append(self._normalizer.normalize_case(observation))

    def append_query_observation(self, *, observation: QueryObservation) -> StatisticsSnapshot:
        return self._append(self._normalizer.normalize_query(observation))

    def replace_case_observation(
        self,
        *,
        old_observation: CaseObservation,
        new_observation: CaseObservation,
    ) -> StatisticsSnapshot:
        if old_observation.partition != new_observation.partition:
            raise ValueError("replacement observations must belong to the same partition")
        with self._snapshot_store.lock(partition=new_observation.partition):
            current = self._snapshot_store.load(partition=new_observation.partition)
            updated = self._aggregator.replace(
                snapshot=current or StatisticsSnapshot(partition=new_observation.partition),
                old_observation=self._normalizer.normalize_case(old_observation),
                new_observation=self._normalizer.normalize_case(new_observation),
            )
            self._snapshot_store.save(statistics=updated)
            return updated

    def remove_observation(self, *, observation: SemanticObservation) -> StatisticsSnapshot | None:
        with self._snapshot_store.lock(partition=observation.partition):
            current = self._snapshot_store.load(partition=observation.partition)
            if current is None:
                return None
            updated = self._aggregator.remove(
                snapshot=current,
                observation=self._normalizer.normalize(observation),
            )
            self._snapshot_store.save(statistics=updated)
            return updated

    def rebuild_partition_statistics(
        self,
        *,
        partition: str,
        observations: list[SemanticObservation],
    ) -> StatisticsSnapshot:
        with self._snapshot_store.lock(partition=partition):
            normalized = [self._normalizer.normalize(observation) for observation in observations]
            snapshot = self._aggregator.build(partition=partition, observations=normalized)
            self._snapshot_store.save(statistics=snapshot)
            return snapshot

    def _append(self, observation: CaseObservation | QueryObservation) -> StatisticsSnapshot:
        with self._snapshot_store.lock(partition=observation.partition):
            current = self._snapshot_store.load(partition=observation.partition)
            updated = self._aggregator.apply(snapshot=current, observation=observation)
            self._snapshot_store.save(statistics=updated)
            return updated


__all__ = ["StatisticsWriter"]
