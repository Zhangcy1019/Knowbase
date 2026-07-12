from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from internal.models.common import normalize_text
from internal.models.facet import PartitionFacetDefinition
from internal.models.semantic_fields import SemanticFieldSet, normalize_semantic_field_values


def _normalize_profile_dict(raw: Any) -> dict[str, Any]:
    return normalize_semantic_field_values(raw)


def resolve_partition_profile_fields(
    facet_definitions: list[PartitionFacetDefinition] | None,
) -> dict[str, str]:
    fields: dict[str, str] = {}
    for definition in facet_definitions or []:
        key = normalize_text(definition.key)
        if not key:
            continue
        description = normalize_text(definition.description or definition.display_name)
        fields[key] = description
    return fields


def ensure_partition_profile_keys(
    values: Mapping[str, Any] | BaseModel | None,
    *,
    facet_definitions: list[PartitionFacetDefinition] | None = None,
) -> dict[str, Any]:
    normalized_source = _normalize_profile_dict(values)
    output = dict(normalized_source)
    for key in resolve_partition_profile_fields(facet_definitions):
        output.setdefault(key, [])
    return output


class DynamicSemanticProfile(SemanticFieldSet):
    @classmethod
    def from_partition_schema(
        cls,
        values: Mapping[str, Any] | BaseModel | None = None,
        *,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
    ) -> "DynamicSemanticProfile":
        return cls.model_validate(
            ensure_partition_profile_keys(
                values,
                facet_definitions=facet_definitions,
            )
        )

class CaseSemanticProfile(DynamicSemanticProfile):
    pass


class QuerySemanticProfile(DynamicSemanticProfile):
    pass


class CaseSemanticExtractionEnvelope(BaseModel):
    semantic_profile: dict[str, Any] = Field(default_factory=dict)


class QuerySemanticExtractionEnvelope(BaseModel):
    semantic_profile: dict[str, Any] = Field(default_factory=dict)
    hypothetical_answer: str = ""
