"""Deterministic facet coverage assessment."""

from __future__ import annotations

from internal.knowledge.batch.models import BatchWorkingSet
from internal.knowledge.governance.preparation.evidence import GovernanceEvidenceInputs, GovernanceSignalSet
from internal.knowledge.governance.preparation.models import PartitionFacetCoverageAssessment


def _resolve_coverage_score(*, case_count: int, facet_keys: list[str], facet_key_counts: dict[str, int]) -> float | None:
    """Calculate coverage for one complete case population represented by counts."""
    if not facet_keys or case_count <= 0:
        return None
    expected_pairs = case_count * len(facet_keys)
    covered_pairs = sum(
        min(facet_key_counts.get(key, 0), case_count)
        for key in facet_keys
    )
    return round(covered_pairs / expected_pairs, 2)


class CoverageEvaluator:
    """Build coverage evidence without proposing or applying schema changes."""

    def evaluate(
        self,
        *,
        batch_working_set: BatchWorkingSet,
        inputs: GovernanceEvidenceInputs,
        signals: GovernanceSignalSet,
    ) -> PartitionFacetCoverageAssessment:
        # case may leak some facet key
        affected_case_coverage = _resolve_coverage_score(
            case_count=len(signals.affected_case_ids),
            facet_keys=signals.existing_facet_keys,
            facet_key_counts=signals.affected_facet_key_counts,
        )
        baseline_coverage = _resolve_coverage_score(
            case_count=signals.statistics_case_count,
            facet_keys=signals.existing_facet_keys,
            facet_key_counts=signals.statistics_facet_key_counts,
        )
        post_batch_coverage = _resolve_coverage_score(
            case_count=signals.semantic_index_case_count,
            facet_keys=signals.existing_facet_keys,
            facet_key_counts=signals.facet_index_key_counts,
        )
        coverage_delta = (
            round(post_batch_coverage - baseline_coverage, 2)
            if baseline_coverage is not None and post_batch_coverage is not None
            else None
        )
        # not_applicable： no existing facet keys in the partition, so coverage is not applicable
        # inconsistent： existing facet keys are present, but the partition is inconsistent with the statistics snapshot
        # available： existing facet keys are present, and both baseline and post-batch coverage are available
        # incomplete： existing facet keys are present, but either baseline or post-batch coverage is missing
        coverage_status = "not_applicable" if not signals.existing_facet_keys else (
            "inconsistent" if signals.consistency_status == "inconsistent" else
            "available" if baseline_coverage is not None and post_batch_coverage is not None else "incomplete"
        )
        return PartitionFacetCoverageAssessment(
            partition=batch_working_set.partition,
            affected_case_ids=signals.affected_case_ids,
            existing_facet_keys=signals.existing_facet_keys,
            observed_facet_keys=signals.observed_facet_keys,
            coverage_score=post_batch_coverage,
            baseline_coverage=baseline_coverage,
            affected_case_coverage=affected_case_coverage,
            post_batch_coverage=post_batch_coverage,
            coverage_delta=coverage_delta,
            coverage_status=coverage_status,
            missing_key_signals=[
                *signals.missing_key_signals,
                *[f"stable_key:{key}:not_observed" for key in signals.stable_key_gaps],
            ],
            notes=[
                "baseline_coverage is derived from the statistics snapshot; post_batch_coverage is derived from the materialized facet index.",
                f"resource_group_count={len(batch_working_set.resource_groups)}",
                f"partition_status={inputs.partition_status}",
                f"enabled_facet_key_count={len(inputs.enabled_facet_keys)}",
                f"semantic_index_key_count={len(signals.semantic_index_key_counts)}",
                f"facet_index_key_count={len(signals.facet_index_key_counts)}",
                f"semantic_index_case_count={signals.semantic_index_case_count}",
            ],
        )


__all__ = ["CoverageEvaluator"]
