"""Deterministic aggregation of statistics observations."""

from __future__ import annotations

from datetime import datetime, timezone

from internal.knowledge.statistics.models import SemanticObservation, StatisticsSnapshot


class StatisticsAggregator:
    """Maintain snapshots incrementally and rebuild them from observations."""

    def apply(self, *, snapshot: StatisticsSnapshot | None, observation: SemanticObservation) -> StatisticsSnapshot:
        """Apply one observation to the current snapshot in place-like form."""
        current = snapshot or StatisticsSnapshot(partition=observation.partition)
        if current.partition != observation.partition:
            raise ValueError("observation partition does not match statistics snapshot")
        if observation.observation_id in current.applied_observation_ids:
            return current

        data = current.model_copy(deep=True)
        is_case = observation.source == "case"
        if is_case:
            data.case_count += 1
        else:
            data.query_count += 1
        key_stats = data.case_key_stats if is_case else data.query_key_stats
        support_index = data.case_support_index if is_case else data.query_support_index
        for field, mapping in self._fields(observation).items():
            for key, values in mapping.items():
                key_ref = f"{field}:{key}"
                key_stats[key_ref] = key_stats.get(key_ref, 0) + 1
                value_counts = data.value_stats.setdefault(key_ref, {})
                for value in values:
                    value_counts[value] = value_counts.get(value, 0) + 1
                    index_key = f"{key_ref}:{value}"
                    ids = set(support_index.get(index_key, []))
                    ids.add(observation.source_id)
                    support_index[index_key] = sorted(ids)
        data.generated_at = datetime.now(timezone.utc)
        data.applied_observation_ids = sorted(
            {*data.applied_observation_ids, observation.observation_id}
        )
        return data

    def remove(self, *, snapshot: StatisticsSnapshot, observation: SemanticObservation) -> StatisticsSnapshot:
        """Remove one observation's contribution from the current snapshot."""
        if observation.observation_id not in snapshot.applied_observation_ids:
            return snapshot
        data = snapshot.model_copy(deep=True)
        is_case = observation.source == "case"
        if is_case:
            data.case_count = max(0, data.case_count - 1)
        else:
            data.query_count = max(0, data.query_count - 1)
        key_stats = data.case_key_stats if is_case else data.query_key_stats
        support_index = data.case_support_index if is_case else data.query_support_index
        for field, mapping in self._fields(observation).items():
            for key, values in mapping.items():
                key_ref = f"{field}:{key}"
                self._decrement(key_stats, key_ref)
                value_counts = data.value_stats.get(key_ref, {})
                for value in values:
                    self._decrement(value_counts, value)
                    index_key = f"{key_ref}:{value}"
                    ids = set(support_index.get(index_key, []))
                    ids.discard(observation.source_id)
                    if ids:
                        support_index[index_key] = sorted(ids)
                    else:
                        support_index.pop(index_key, None)
                if not value_counts:
                    data.value_stats.pop(key_ref, None)
        data.generated_at = datetime.now(timezone.utc)
        data.applied_observation_ids = [
            item for item in data.applied_observation_ids if item != observation.observation_id
        ]
        return data

    def replace(
        self,
        *,
        snapshot: StatisticsSnapshot,
        old_observation: SemanticObservation,
        new_observation: SemanticObservation,
    ) -> StatisticsSnapshot:
        return self.apply(
            snapshot=self.remove(snapshot=snapshot, observation=old_observation),
            observation=new_observation,
        )

    @staticmethod
    def _decrement(values: dict[str, int], key: str) -> None:
        count = values.get(key, 0) - 1
        if count > 0:
            values[key] = count
        else:
            values.pop(key, None)

    def build(self, *, partition: str, observations: list[SemanticObservation]) -> StatisticsSnapshot:
        snapshot: StatisticsSnapshot | None = StatisticsSnapshot(partition=partition)
        for observation in observations:
            if observation.partition == partition:
                snapshot = self.apply(snapshot=snapshot, observation=observation)
        return snapshot

    @staticmethod
    def _fields(observation: SemanticObservation) -> dict[str, dict[str, list[str]]]:
        return {
            "facet": observation.facets,
            "semantic_profile": observation.semantic_profile,
            "fact": observation.facts,
        }


__all__ = ["StatisticsAggregator"]
