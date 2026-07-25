"""Statistics writer capability skeleton."""

from __future__ import annotations

from internal.knowledge.statistics.models import CaseObservation, QueryObservation, StatisticsSnapshot


class StatisticsWriter:
    """Accept observations and produce updated statistics snapshots."""

    def append_case_observation(self, *, observation: CaseObservation) -> None:
        raise NotImplementedError

    def append_query_observation(self, *, observation: QueryObservation) -> None:
        raise NotImplementedError

    def rebuild_partition_statistics(self, *, partition: str) -> StatisticsSnapshot:
        raise NotImplementedError


__all__ = ["StatisticsWriter"]
