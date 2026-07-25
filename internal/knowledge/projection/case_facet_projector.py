"""Case facet projection skeleton."""

from __future__ import annotations

from internal.knowledge.projection.models import CaseProjectionChange


class CaseFacetProjector:
    """Project case facets from case truth under one partition facet schema."""

    def __init__(self, *, facet_resolver):
        self._facet_resolver = facet_resolver

    def project_one(self, *, case, schema) -> CaseProjectionChange | None:
        projected = self._facet_resolver.project_from_semantic_profile(
            semantic_profile=case.semantic_profile,
            facet_definitions=schema.definitions,
        )
        before = case.facets.model_dump()
        after = projected.model_dump()
        changed_keys = sorted(
            key for key in set(before) | set(after) if before.get(key, []) != after.get(key, [])
        )
        if not changed_keys:
            return None
        return CaseProjectionChange(
            partition=case.partition,
            case_id=case.case_id,
            before_facets=before,
            after_facets=after,
            changed_keys=changed_keys,
        )
