"""Statistics snapshot storage capability skeleton."""

from __future__ import annotations

from contextlib import contextmanager

from internal.knowledge.statistics.models import CaseStatisticsSnapshot, QueryStatisticsSnapshot


class StatisticsStore:
    """Persist the current partition snapshot working file.

    Historical versions, diffs, and rollback are handled by the Git-backed
    Knowledge patch workflow rather than by this store.
    """

    def __init__(self, *, repository) -> None:
        self._repository = repository

    def load(self, *, partition: str) -> CaseStatisticsSnapshot | QueryStatisticsSnapshot | None:
        return self._repository.get(partition)

    def save(self, *, statistics: CaseStatisticsSnapshot | QueryStatisticsSnapshot) -> None:
        self._repository.upsert(statistics)

    @contextmanager
    def lock(self, *, partition: str):
        """Lock one partition for a complete statistics update."""
        with self._repository.lock(partition):
            yield


__all__ = ["StatisticsStore"]
