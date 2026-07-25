"""Statistics reader capability skeleton."""

from __future__ import annotations

from internal.knowledge.statistics.models import CaseSupportQuery, StatisticsSnapshot, StatisticsSource


class StatisticsReader:
    """Read partition statistics without mutating them."""

    def __init__(self, *, store) -> None:
        self._store = store

    def load_partition_statistics(self, *, partition: str) -> StatisticsSnapshot | None:
        return self._store.load(partition=partition)

    def query_key_stats(self, *, partition: str, source: StatisticsSource = "case") -> dict[str, int]:
        snapshot = self.load_partition_statistics(partition=partition)
        if snapshot is None:
            return {}
        return snapshot.case_key_stats if source == "case" else snapshot.query_key_stats

    def find_supporting_cases(self, *, partition: str, query: CaseSupportQuery) -> list[str]:
        snapshot = self.load_partition_statistics(partition=partition)
        if snapshot is None:
            return []
        support_index = snapshot.case_support_index
        matched: set[str] = set()
        for value in query.filters:
            key_ref = f"{value.field}:{value.key}"
            for candidate in value.values:
                matched.update(support_index.get(f"{key_ref}:{candidate}", []))
        if not query.filters:
            return []
        if query.match_mode == "all":
            result_sets = [
                {
                    case_id
                    for candidate in value.values
                    for case_id in support_index.get(f"{value.field}:{value.key}:{candidate}", [])
                }
                for value in query.filters
            ]
            matched = set.intersection(*result_sets) if result_sets else set()
        result = sorted(matched)
        return result[: query.limit] if query.limit is not None else result


__all__ = ["StatisticsReader"]
