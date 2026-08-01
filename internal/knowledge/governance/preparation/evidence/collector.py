"""Derive reusable governance signals from loaded resources."""

from __future__ import annotations

from dataclasses import dataclass

from internal.knowledge.batch.models import BatchWorkingSet
from internal.knowledge.governance.preparation.evidence.loader import GovernanceEvidenceInputs
from internal.models.facet import PartitionFacetIndex
from internal.models.partition_semantic_index import PartitionSemanticIndex


def _collect_facet_index_key_counts(facet_index: PartitionFacetIndex | None) -> dict[str, int]:
    if facet_index is None:
        return {}
    return {item.key.strip(): int(item.count) for item in facet_index.key_stats if item.key.strip()}


def _collect_semantic_index_key_counts(semantic_index: PartitionSemanticIndex | None) -> dict[str, int]:
    if semantic_index is None:
        return {}
    return {item.key.strip(): int(item.count) for item in semantic_index.key_stats if item.key.strip()}


def _resolve_index_case_count(semantic_index: PartitionSemanticIndex | None) -> int:
    if semantic_index is None:
        return 0
    value = semantic_index.metadata.get("case_count", 0)
    return int(value) if isinstance(value, (int, float, str)) else 0


@dataclass(slots=True)
class GovernanceSignalSet:
    """Normalized signals shared by coverage and proposal evaluation."""

    observed_facet_keys: list[str]
    existing_facet_keys: list[str]
    affected_case_ids: list[str]
    semantic_candidate_keys: list[str]
    affected_semantic_profile_key_counts: dict[str, int]
    affected_facet_key_counts: dict[str, int]
    semantic_index_key_counts: dict[str, int] # Count of cases per facet key in the partition's semantic index
    facet_index_key_counts: dict[str, int] # Count of cases per facet key in the partition's facet index
    semantic_index_case_count: int
    statistics_case_count: int
    statistics_semantic_key_counts: dict[str, int]
    statistics_facet_key_counts: dict[str, int]
    consistency_status: str # "consistent", "inconsistent", or "unavailable", meaning whether the statistics snapshot and indexes are consistent with each other
    consistency_mismatches: list[dict[str, object]] # List of mismatches between the statistics snapshot and indexes, if any
    missing_key_signals: list[str] # Semantic signals missing from affected cases while the corresponding facet schema coverage is incomplete.
    stable_key_gaps: list[str] # Existing facet keys with no affected-case, semantic-index, or facet-index support.


class GovernanceSignalCollector:
    """Convert raw resources and batch changes into deterministic signals."""

    def collect(
        self,
        *,
        batch_working_set: BatchWorkingSet,
        inputs: GovernanceEvidenceInputs,
    ) -> GovernanceSignalSet:
        observed_facet_keys = list(dict.fromkeys(batch_working_set.observed_facet_keys))
        existing_facet_keys = list(dict.fromkeys(inputs.enabled_facet_keys))
        affected_case_ids = [item.case_id for item in inputs.affected_cases]
        affected_semantic_profile_key_counts = self._collect_profile_key_counts(inputs.affected_cases)
        semantic_candidate_keys = [key for key in affected_semantic_profile_key_counts if key not in existing_facet_keys]
        affected_facet_key_counts = self._collect_facet_key_counts(inputs.affected_cases)
        facet_index_key_counts = _collect_facet_index_key_counts(inputs.facet_index)
        semantic_index_key_counts = _collect_semantic_index_key_counts(inputs.semantic_index)
        semantic_index_case_count = _resolve_index_case_count(inputs.semantic_index)
        statistics_case_count = self._statistics_case_count(inputs.statistics_snapshot)
        statistics_semantic_key_counts = self._snapshot_key_counts(
            inputs.statistics_snapshot,
            field="semantic_profile",
        )
        statistics_facet_key_counts = self._snapshot_key_counts(
            inputs.statistics_snapshot,
            field="facet",
        )
        consistency_status, consistency_mismatches = self._compare_statistics_and_indexes(
            statistics_case_count=statistics_case_count,
            statistics_semantic_key_counts=statistics_semantic_key_counts,
            statistics_facet_key_counts=statistics_facet_key_counts,
            semantic_index=inputs.semantic_index,
            facet_index=inputs.facet_index,
        )

        # Detect missing key signals for cases that have semantic profile changes but no facet matches
        case_by_id = {item.case_id: item for item in inputs.affected_cases}
        missing_key_signals = [
            f"resource_group:{group.resource_id}:semantic_profile_changed_without_facet_match"
            for group in batch_working_set.resource_groups
            if (
                group.resource_type == "case"
                and "semantic_profile" in group.changed_fields
                and not (
                    case_by_id.get(group.resource_id).facets
                    if case_by_id.get(group.resource_id) is not None
                    else group.observed_facets
                )
            )
        ]

        # Detect stable key gaps for keys that exist in the partition but have no affected-case or index counts.
        stable_key_gaps = [
            key
            for key in existing_facet_keys
            if (
                affected_semantic_profile_key_counts.get(key, 0) == 0
                and affected_facet_key_counts.get(key, 0) == 0
                and semantic_index_key_counts.get(key, 0) == 0
                and facet_index_key_counts.get(key, 0) == 0
            )
        ]
        return GovernanceSignalSet(
            observed_facet_keys=observed_facet_keys,
            existing_facet_keys=existing_facet_keys,
            affected_case_ids=affected_case_ids,
            semantic_candidate_keys=semantic_candidate_keys,
            affected_semantic_profile_key_counts=affected_semantic_profile_key_counts,
            affected_facet_key_counts=affected_facet_key_counts,
            semantic_index_key_counts=semantic_index_key_counts,
            facet_index_key_counts=facet_index_key_counts,
            semantic_index_case_count=semantic_index_case_count,
            statistics_case_count=statistics_case_count,
            statistics_semantic_key_counts=statistics_semantic_key_counts,
            statistics_facet_key_counts=statistics_facet_key_counts,
            consistency_status=consistency_status,
            consistency_mismatches=consistency_mismatches,
            missing_key_signals=list(missing_key_signals),
            stable_key_gaps=list(dict.fromkeys(stable_key_gaps)),
        )

    @staticmethod
    def _collect_profile_key_counts(cases) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in cases:
            for key, raw_values in case.semantic_profile.ordered_items():
                normalized_key = str(key).strip()
                if normalized_key and raw_values:
                    counts[normalized_key] = counts.get(normalized_key, 0) + 1
        return counts

    @staticmethod
    def _collect_facet_key_counts(cases) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in cases:
            for key, raw_values in case.facets.ordered_items():
                normalized_key = str(key).strip()
                if normalized_key and raw_values:
                    counts[normalized_key] = counts.get(normalized_key, 0) + 1
        return counts

    @staticmethod
    def _statistics_case_count(snapshot) -> int:
        return int(getattr(snapshot, "case_count", 0) or 0) if snapshot is not None else 0

    @staticmethod
    def _snapshot_key_counts(snapshot, *, field: str) -> dict[str, int]:
        if snapshot is None:
            return {}
        prefix = f"{field}:"
        result: dict[str, int] = {}
        for raw_key, raw_count in getattr(snapshot, "case_key_stats", {}).items():
            key = str(raw_key)
            if not key.startswith(prefix):
                continue
            try:
                count = int(raw_count)
            except (TypeError, ValueError):
                continue
            normalized = key[len(prefix):].strip()
            if normalized:
                result[normalized] = count
        return result

    # compare statistics snapshot counts with index counts to detect mismatches
    @staticmethod
    def _compare_statistics_and_indexes(
        *,
        statistics_case_count: int,
        statistics_semantic_key_counts: dict[str, int],
        statistics_facet_key_counts: dict[str, int],
        semantic_index,
        facet_index,
    ) -> tuple[str, list[dict[str, object]]]:
        if statistics_case_count <= 0:
            return "unavailable", []
        mismatches: list[dict[str, object]] = []
        # Semantic profiles are source-derived and must stay consistent with
        # the materialized semantic index. Facets are schema projections: a
        # governance apply can change the facet index without changing the
        # case observation that produced the statistics snapshot. They remain
        # useful evidence, but must not block the next drain as stale state.
        for index_name, index, snapshot_counts in (
            ("semantic_index", semantic_index, statistics_semantic_key_counts),
        ):
            if index is None:
                # index is missing
                mismatches.append({"source": index_name, "kind": "missing_index"})
                continue
            index_case_count = int((getattr(index, "metadata", {}) or {}).get("case_count", 0) or 0)
            # Compare case counts
            if index_case_count and index_case_count != statistics_case_count:
                mismatches.append({
                    "source": index_name,
                    "kind": "case_count_mismatch",
                    "statistics_case_count": statistics_case_count,
                    "index_case_count": index_case_count,
                })
            index_counts = {
                item.key.strip(): int(item.count)
                for item in getattr(index, "key_stats", [])
                if item.key.strip()
            }
            for key in sorted(set(snapshot_counts) | set(index_counts)):
                snapshot_count = snapshot_counts.get(key, 0)
                index_count = index_counts.get(key, 0)
                # Compare key counts
                if snapshot_count != index_count:
                    mismatches.append({
                        "source": index_name,
                        "kind": "key_count_mismatch",
                        "key": key,
                        "statistics_count": snapshot_count,
                        "index_count": index_count,
                    })
        return ("inconsistent", mismatches) if mismatches else ("consistent", [])


__all__ = ["GovernanceSignalCollector", "GovernanceSignalSet"]
