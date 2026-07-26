"""Facet freeze and cooldown skeleton."""

from __future__ import annotations


class FacetFreezePolicy:
    """Apply freeze windows and cooldown constraints to schema proposals."""

    def evaluate(self, *, partition: str, proposal):
        raise NotImplementedError
