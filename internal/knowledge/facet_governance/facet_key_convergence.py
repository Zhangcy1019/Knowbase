"""Facet key convergence skeleton."""

from __future__ import annotations


class FacetKeyConvergencePlanner:
    """Plan promotion and demotion proposals for partition facet keys."""

    def propose(self, *, partition: str, semantic_index, current_schema):
        raise NotImplementedError
