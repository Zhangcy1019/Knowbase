"""Top-level knowledge patch models."""

from __future__ import annotations

from dataclasses import dataclass, field

from internal.knowledge.model.case_facet_patch import CaseFacetPatch
from internal.knowledge.model.facet_schema_patch import PartitionFacetSchemaPatch


@dataclass(slots=True)
class KnowledgePatch:
    """Batch-scoped reversible knowledge patch."""

    patch_id: str = ""
    batch_id: str = ""
    partition: str = ""
    created_at: str = ""
    risk_level: str = "medium"
    reversible: bool = True
    partition_facet_schema_patch: PartitionFacetSchemaPatch | None = None
    case_facet_patches: list[CaseFacetPatch] = field(default_factory=list)
    metrics_snapshot: dict[str, object] = field(default_factory=dict)
    circuit_breaker_report: dict[str, object] = field(default_factory=dict)
    affected_case_ids: list[str] = field(default_factory=list)
    summary: str = ""
