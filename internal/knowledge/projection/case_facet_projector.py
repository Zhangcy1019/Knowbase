"""Case facet projection skeleton."""

from __future__ import annotations


class CaseFacetProjector:
    """Project case facets from case truth under one partition facet schema."""

    def project_many(self, *, partition: str, schema, case_ids: list[str]):
        raise NotImplementedError
