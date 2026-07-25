"""Partition facet-schema patch models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PartitionFacetSchemaPatch:
    """One reversible schema-level patch for partition facets."""

    partition: str = ""
    before_schema_version: str = ""
    after_schema_version: str = ""
    added_keys: list[str] = field(default_factory=list)
    removed_keys: list[str] = field(default_factory=list)
    renamed_keys: dict[str, str] = field(default_factory=dict)
    frozen_keys: list[str] = field(default_factory=list)
