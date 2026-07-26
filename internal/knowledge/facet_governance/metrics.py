"""Facet governance statistics and threshold calculations."""

from __future__ import annotations

from internal.models.facet import PartitionFacetIndex
from internal.models.partition_semantic_index import PartitionSemanticIndex


class FacetGovernanceMetrics:
    """Calculate reusable signals for facet governance decisions."""

    @staticmethod
    def collect_facet_index_key_counts(*, facet_index: PartitionFacetIndex | None) -> dict[str, int]:
        if facet_index is None:
            return {}
        return {item.key.strip(): int(item.count) for item in facet_index.key_stats if item.key.strip()}

    @staticmethod
    def collect_semantic_index_key_counts(*, semantic_index: PartitionSemanticIndex | None) -> dict[str, int]:
        if semantic_index is None:
            return {}
        return {item.key.strip(): int(item.count) for item in semantic_index.key_stats if item.key.strip()}

    @staticmethod
    def resolve_index_case_count(*, semantic_index: PartitionSemanticIndex | None) -> int:
        if semantic_index is None:
            return 0
        value = semantic_index.metadata.get("case_count", 0)
        return int(value) if isinstance(value, (int, float, str)) else 0

    @staticmethod
    def resolve_promotable_keys(*, existing_keys: list[str], index_key_counts: dict[str, int], index_case_count: int) -> list[str]:
        if index_case_count <= 0:
            return []
        threshold = max(2, int(index_case_count * 0.3))
        return sorted(key for key, count in index_key_counts.items() if key not in existing_keys and count >= threshold)

    @staticmethod
    def resolve_demotable_keys(*, existing_keys: list[str], touched_keys: list[str], semantic_index_key_counts: dict[str, int], facet_index_key_counts: dict[str, int]) -> list[str]:
        return sorted(
            key for key in existing_keys
            if key not in touched_keys
            and semantic_index_key_counts.get(key, 0) == 0
            and facet_index_key_counts.get(key, 0) == 0
        )

    @staticmethod
    def resolve_coverage_score(*, sampled_case_ids: list[str], missing_key_signals: list[str], existing_keys: list[str], index_key_counts: dict[str, int], index_case_count: int) -> float:
        if not sampled_case_ids and not existing_keys and index_case_count <= 0:
            return 1.0
        score = 1.0
        if missing_key_signals:
            score -= min(0.4, 0.1 * len(missing_key_signals))
        if existing_keys:
            score -= min(0.3, 0.05 * sum(1 for key in existing_keys if index_key_counts.get(key, 0) == 0))
        if sampled_case_ids and not index_key_counts:
            score -= 0.2
        return max(0.0, round(score, 2))


__all__ = ["FacetGovernanceMetrics"]
