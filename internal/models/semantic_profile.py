from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from internal.models.common import normalize_string_list, normalize_text
from internal.models.facet import PartitionFacetDefinition


def _normalize_profile_dict(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, BaseModel):
        raw = raw.model_dump()
    if not isinstance(raw, Mapping):
        return {}

    normalized: dict[str, Any] = {}
    for raw_key, raw_value in raw.items():
        key = normalize_text(raw_key)
        if not key:
            continue
        normalized[key] = normalize_string_list(raw_value)
    return normalized


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


class DynamicSemanticProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def normalize_dynamic_values(cls, value: Any) -> dict[str, Any]:
        return _normalize_profile_dict(value)

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

    def get_list(self, key: str) -> list[str]:
        value = self.model_dump().get(key)
        return normalize_string_list(value)

    def ordered_items(self, *, exclude: Iterable[str] = ()) -> list[tuple[str, Any]]:
        excluded = {normalize_text(item) for item in exclude if normalize_text(item)}
        return [
            (key, value)
            for key, value in self.model_dump().items()
            if key not in excluded
        ]


class CaseSemanticProfile(DynamicSemanticProfile):
    pass


class QuerySemanticProfile(DynamicSemanticProfile):
    pass


class CaseSemanticExtractionEnvelope(BaseModel):
    semantic_profile: dict[str, Any] = Field(default_factory=dict)


class QuerySemanticExtractionEnvelope(BaseModel):
    semantic_profile: dict[str, Any] = Field(default_factory=dict)
    hypothetical_answer: str = ""
