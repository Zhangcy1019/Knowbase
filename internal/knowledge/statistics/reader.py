"""Statistics reader capability skeleton."""

from __future__ import annotations

from internal.knowledge.statistics.models import CaseSupportQuery, StatisticsSnapshot, StatisticsSource


class StatisticsReader:
    """Read partition statistics without mutating them."""

    def load_partition_statistics(self, *, partition: str) -> StatisticsSnapshot | None:
        raise NotImplementedError

    def query_key_stats(self, *, partition: str, source: StatisticsSource = "case") -> dict[str, int]:
        raise NotImplementedError

    def find_supporting_cases(self, *, partition: str, query: CaseSupportQuery) -> list[str]:
        raise NotImplementedError


__all__ = ["StatisticsReader"]
