"""Case facet patch models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CaseFacetPatch:
    """One reversible case-facet patch under a partition schema version."""

    case_id: str = ""
    partition: str = ""
    schema_version: str = ""
    added_facets: dict[str, list[str]] = field(default_factory=dict)
    removed_facets: dict[str, list[str]] = field(default_factory=dict)
    updated_facets: dict[str, list[str]] = field(default_factory=dict)
