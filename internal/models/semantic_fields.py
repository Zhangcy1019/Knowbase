from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from internal.models.common import normalize_string_list, normalize_text


def normalize_semantic_field_values(raw: Any) -> dict[str, list[str]]:
    if raw is None:
        return {}
    if isinstance(raw, SemanticFieldSet):
        return raw.model_dump()
    if isinstance(raw, BaseModel):
        raw = raw.model_dump()
    if not isinstance(raw, Mapping):
        return {}

    normalized: dict[str, list[str]] = {}
    for raw_key, raw_value in raw.items():
        key = normalize_text(raw_key)
        if not key:
            continue
        normalized[key] = normalize_string_list(raw_value)
    return normalized


class SemanticFieldSet(BaseModel):
    """Shared key->values structure used by open and stable semantic fields."""

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    def normalize_dynamic_values(cls, value: Any) -> dict[str, list[str]]:
        return normalize_semantic_field_values(value)

    def get_list(self, key: str) -> list[str]:
        value = self.model_dump().get(normalize_text(key))
        return normalize_string_list(value)

    def ordered_items(self, *, exclude: Iterable[str] = ()) -> list[tuple[str, list[str]]]:
        excluded = {normalize_text(item) for item in exclude if normalize_text(item)}
        return [
            (key, value)
            for key, value in self.model_dump().items()
            if key not in excluded
        ]

    def get(self, key: str, default: Any = None) -> Any:
        return self.model_dump().get(normalize_text(key), default)

    def items(self) -> list[tuple[str, list[str]]]:
        return list(self.model_dump().items())

    def keys(self) -> list[str]:
        return list(self.model_dump().keys())

    def values(self) -> list[list[str]]:
        return list(self.model_dump().values())

    def __iter__(self) -> Iterator[str]:
        return iter(self.model_dump())

    def __len__(self) -> int:
        return len(self.model_dump())

