"""Statistics snapshot storage capability skeleton."""

from __future__ import annotations

from internal.knowledge.statistics.models import StatisticsSnapshot


class StatisticsStore:
    """Persist the current partition snapshot working file.

    Historical versions, diffs, and rollback are handled by the Git-backed
    Knowledge patch workflow rather than by this store.
    """

    def load(self, *, partition: str) -> StatisticsSnapshot | None:
        raise NotImplementedError

    def save(self, *, statistics: StatisticsSnapshot) -> None:
        raise NotImplementedError


__all__ = ["StatisticsStore"]
