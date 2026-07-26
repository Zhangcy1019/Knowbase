"""Partition fit metric skeleton."""

from __future__ import annotations


class PartitionFitMetrics:
    """Compute fit and coverage metrics for partition schema proposals."""

    def evaluate(self, *, partition: str, semantic_index, schema):
        raise NotImplementedError
