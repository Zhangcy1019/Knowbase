"""Project stable case facets from the dynamic semantic profile."""

from __future__ import annotations
from internal.models import DynamicSemanticProfile, PartitionFacetDefinition


class KnowbaseCaseFacetResolver:
    """Project and canonicalize stable facet keys from the current schema."""

    def project_from_semantic_profile(
        self,
        *,
        semantic_profile: DynamicSemanticProfile | dict[str, list[str]],
        facet_definitions: list[PartitionFacetDefinition],
    ) -> dict[str, list[str]]:
        if isinstance(semantic_profile, DynamicSemanticProfile):
            profile_map = semantic_profile.model_dump()
        else:
            profile_map = dict(semantic_profile)
        return self.normalize(
            facets={
                definition.key: profile_map.get(definition.key, [])
                for definition in facet_definitions
                if definition.enabled and definition.key.strip()
            },
            facet_definitions=facet_definitions,
        )

    def normalize(
        self,
        *,
        facets: dict[str, list[str]],
        facet_definitions: list[PartitionFacetDefinition],
    ) -> dict[str, list[str]]:
        definition_map = {
            definition.key.strip().lower(): definition
            for definition in facet_definitions
            if definition.enabled and definition.key.strip()
        }
        resolved: dict[str, list[str]] = {}
        for raw_key, raw_values in facets.items():
            normalized_key = str(raw_key).strip().lower()
            definition = definition_map.get(normalized_key)
            if definition is None:
                continue
            key = definition.key.strip()
            values: list[str] = []
            for raw_value in raw_values:
                value = str(raw_value).strip()
                if not value:
                    continue
                if value and value not in values:
                    values.append(value)
            if values:
                resolved[key] = values
        return resolved
