"""Partition-level semantic statistics and reverse-index models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PartitionSemanticIndex:
    """Aggregated semantic statistics for one partition."""

    partition: str = ""
    updated_at: str = ""
    source_case_count: int = 0
    batch_cursor: str = ""
    key_stats: dict[str, dict[str, object]] = field(default_factory=dict)
    key_value_stats: dict[str, dict[str, dict[str, object]]] = field(default_factory=dict)
    key_alias_clusters: dict[str, list[str]] = field(default_factory=dict)
    case_support_index: dict[str, list[str]] = field(default_factory=dict)
    value_support_index: dict[str, dict[str, list[str]]] = field(default_factory=dict)
    temporal_support_windows: dict[str, list[dict[str, object]]] = field(default_factory=dict)
