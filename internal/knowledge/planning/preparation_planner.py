"""Deterministic backlog preparation planner for batch-derived runtime dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from internal.models import (
    BatchActionCandidate,
    BatchPreparation,
    BatchWorkingSet,
    KnowbaseCaseDocument,
    PartitionFacetCoverageAssessment,
    PartitionFacetSchemaProposal,
    PartitionRebuildRecommendation,
)
from internal.models.facet import PartitionFacetIndex
from internal.models.partition_semantic_index import PartitionSemanticIndex
from internal.ports import CaseReadPort, PartitionProfileReadPort, PartitionReadPort


@dataclass(slots=True)
class GovernanceAssessmentInputs:
    partition_status: str
    partition_scenario_description: str
    enabled_facet_keys: list[str]
    affected_cases: list[KnowbaseCaseDocument]
    facet_index: PartitionFacetIndex | None
    semantic_index: PartitionSemanticIndex | None


class BacklogPreparationPlanner:
    """Build one preparation plan from one backlog working set."""

    def __init__(
        self,
        *,
        partition_service: PartitionReadPort | PartitionProfileReadPort,
        case_repository: CaseReadPort,
    ):
        self._partition_service = partition_service
        self._case_repository = case_repository

    def build_preparation(self, *, batch_working_set: BatchWorkingSet) -> BatchPreparation:
        inputs = self._load_inputs(batch_working_set=batch_working_set)
        touched_keys = list(dict.fromkeys(batch_working_set.affected_facet_keys))
        existing_keys = list(dict.fromkeys(inputs.enabled_facet_keys))
        sampled_case_ids = [item.case_id for item in inputs.affected_cases]
        sampled_profile_key_counts = self._collect_observed_profile_key_counts(cases=inputs.affected_cases)
        sampled_facet_key_counts = self._collect_observed_facet_key_counts(cases=inputs.affected_cases)
        facet_index_key_counts = self._collect_facet_index_key_counts(facet_index=inputs.facet_index)
        index_key_counts = self._collect_index_key_counts(semantic_index=inputs.semantic_index)
        index_case_count = self._resolve_index_case_count(semantic_index=inputs.semantic_index)

        case_by_id = {item.case_id: item for item in inputs.affected_cases}
        missing_key_signals = [
            f"resource_group:{group.resource_id}:semantic_profile_changed_without_facet_match"
            for group in batch_working_set.resource_groups
            if (
                group.resource_type == "case"
                and "semantic_profile" in group.changed_fields
                and not (case_by_id.get(group.resource_id).facets if case_by_id.get(group.resource_id) is not None else group.observed_facets)
            )
        ]
        all_missing_signals = list(missing_key_signals)
        promotable_keys = self._resolve_promotable_keys(
            existing_keys=existing_keys,
            index_key_counts=index_key_counts,
            index_case_count=index_case_count,
        )
        demotable_keys = self._resolve_demotable_keys(
            existing_keys=existing_keys,
            touched_keys=touched_keys,
            semantic_index_key_counts=index_key_counts,
            facet_index_key_counts=facet_index_key_counts,
        )
        coverage_score = self._resolve_coverage_score(
            sampled_case_ids=sampled_case_ids,
            missing_key_signals=missing_key_signals,
            existing_keys=existing_keys,
            index_key_counts=index_key_counts,
            index_case_count=index_case_count,
        )
        stable_key_gaps = [
            key
            for key in existing_keys
            if (
                sampled_profile_key_counts.get(key, 0) == 0
                and sampled_facet_key_counts.get(key, 0) == 0
                and index_key_counts.get(key, 0) == 0
                and facet_index_key_counts.get(key, 0) == 0
            )
        ]
        ambiguous_keys = list(
            dict.fromkeys(
                [
                    *[key for key in touched_keys if key not in existing_keys],
                    *promotable_keys,
                    *stable_key_gaps,
                ]
            )
        )

        coverage = PartitionFacetCoverageAssessment(
            partition=batch_working_set.partition,
            sampled_case_ids=sampled_case_ids,
            existing_keys=existing_keys,
            touched_keys=touched_keys,
            coverage_score=coverage_score,
            missing_key_signals=[*all_missing_signals, *[f"stable_key:{key}:not_observed" for key in stable_key_gaps]],
            ambiguous_keys=ambiguous_keys,
            notes=[
                "Coverage assessment was derived from recent case events plus partition semantic-index statistics.",
                f"resource_group_count={len(batch_working_set.resource_groups)}",
                f"partition_status={inputs.partition_status}",
                f"enabled_facet_key_count={len(inputs.enabled_facet_keys)}",
                f"semantic_index_key_count={len(index_key_counts)}",
                f"facet_index_key_count={len(facet_index_key_counts)}",
                f"semantic_index_case_count={index_case_count}",
                f"promotable_key_count={len(promotable_keys)}",
                f"demotable_key_count={len(demotable_keys)}",
            ],
        )
        schema_proposal = PartitionFacetSchemaProposal(
            partition=batch_working_set.partition,
            rationale=(
                "Review partition facet keys for promotion or demotion based on partition semantic-index frequency signals."
                if (all_missing_signals or promotable_keys or demotable_keys)
                else "Current partition facet keys appear sufficient against the current semantic-index snapshot."
            ),
            suggested_new_keys=promotable_keys,
            suggested_updated_keys=[key for key in touched_keys if key in existing_keys and (all_missing_signals or stable_key_gaps)],
            suggested_removed_keys=demotable_keys,
            notes=[
                "Schema proposal is assessment-only in the current skeleton.",
                "Key mutations should be confirmed through the dedicated partition configuration flow.",
                f"scenario={inputs.partition_scenario_description}",
                "Promotion means elevating one open semantic_profile key into stable facet schema.",
                "Demotion means retiring one stable facet key back into open semantic_profile only.",
                "Promotion and demotion are driven primarily by partition semantic-index persistence, not one batch alone.",
            ],
        )
        rebuild_recommendation = PartitionRebuildRecommendation(
            partition=batch_working_set.partition,
            rebuild_scope="partial" if sampled_case_ids else "none",
            target_case_ids=sampled_case_ids,
            target_facet_keys=list(dict.fromkeys([*touched_keys, *promotable_keys, *demotable_keys])),
            reason=(
                "Recent case updates may require recomputing case facets under the current partition schema."
                if not (promotable_keys or demotable_keys)
                else "Recent case updates plus semantic-index drift suggest reviewing facet schema and rebuilding affected case facets."
            ),
            estimated_change_count=len(sampled_case_ids),
            risk_level="medium" if sampled_case_ids or all_missing_signals or promotable_keys or demotable_keys else "low",
            notes=[
                "Preparation planning focuses on semantic-index-backed facet coverage and refreshing affected case facets.",
                f"affected_case_count={len(inputs.affected_cases)}",
            ],
        )

        candidates: list[BatchActionCandidate] = []
        for index, group in enumerate(sorted(batch_working_set.resource_groups, key=lambda item: (item.priority, item.group_id))):
            if group.is_cancelled_out:
                candidates.append(
                    BatchActionCandidate(
                        candidate_id=f"candidate:{index}:{group.resource_type}:{group.resource_id}:ignore",
                        target_type=group.resource_type,
                        target_id=group.resource_id,
                        action_type="ignore",
                        source_event_ids=group.event_ids,
                        reason="Create/delete lifecycle cancelled out inside the same batch.",
                        risk_level="low",
                    )
                )
                continue
            if group.resource_type != "case":
                continue
            candidates.append(
                BatchActionCandidate(
                    candidate_id=f"candidate:{index}:partition:{group.partition}:assess_partition_facets",
                    target_type="partition",
                    target_id=group.partition,
                    action_type="assess_partition_facets",
                    source_event_ids=group.event_ids,
                    reason="Recent case updates should be aggregated into one facet-coverage assessment.",
                    risk_level="low",
                )
            )
            candidates.append(
                BatchActionCandidate(
                    candidate_id=f"candidate:{index}:case:{group.resource_id}:refresh_representation",
                    target_type="case",
                    target_id=group.resource_id,
                    action_type="refresh_selected_case_representation",
                    source_event_ids=group.event_ids,
                    reason="Changed case should refresh summary and semantic_profile.",
                    risk_level="low",
                )
            )
            candidates.append(
                BatchActionCandidate(
                    candidate_id=f"candidate:{index}:case:{group.resource_id}:refresh_facets",
                    target_type="case",
                    target_id=group.resource_id,
                    action_type="refresh_selected_case_facets",
                    source_event_ids=group.event_ids,
                    reason="Changed case should refresh resolved stable facets under current schema.",
                    risk_level="low",
                )
            )
            if promotable_keys or demotable_keys:
                candidates.append(
                    BatchActionCandidate(
                        candidate_id=f"candidate:{index}:partition:{group.partition}:review_facet_schema",
                        target_type="partition",
                        target_id=group.partition,
                        action_type="review_facet_schema_evolution",
                        source_event_ids=group.event_ids,
                        reason="Partition semantic-index signals suggest facet-key promotion or demotion review.",
                        risk_level="medium",
                        metadata={
                            "promotable_keys": promotable_keys,
                            "demotable_keys": demotable_keys,
                            "semantic_index_case_count": index_case_count,
                        },
                    )
                )

        return BatchPreparation(
            summary=f"Prepared batch {batch_working_set.batch_id} into {len(candidates)} resource action candidate(s).",
            risk_level=rebuild_recommendation.risk_level,
            requires_review=False,
            candidates=candidates,
            facet_coverage_assessment=coverage,
            schema_proposal=schema_proposal,
            rebuild_recommendation=rebuild_recommendation,
            notes=[
                "Preparation planning focuses on semantic-index-backed facet coverage and refresh needs derived from recent case updates.",
                f"resource_group_count={len(batch_working_set.resource_groups)}",
                f"loaded_case_count={len(inputs.affected_cases)}",
            ],
        )

    def _load_inputs(self, *, batch_working_set: BatchWorkingSet) -> GovernanceAssessmentInputs:
        partition = self._partition_service.get_partition(batch_working_set.partition)
        facet_schema = self._partition_service.get_facet_schema(batch_working_set.partition)
        definitions = [] if facet_schema is None else [item for item in facet_schema.definitions if item.enabled]
        enabled_facet_keys = [item.key for item in definitions if item.key.strip()]
        affected_cases = self._case_repository.get_many(list(dict.fromkeys(batch_working_set.affected_case_ids)))
        return GovernanceAssessmentInputs(
            partition_status="missing" if partition is None else partition.status,
            partition_scenario_description="" if partition is None else partition.scenario_description,
            enabled_facet_keys=enabled_facet_keys,
            affected_cases=affected_cases,
            facet_index=self._partition_service.get_facet_index(batch_working_set.partition),
            semantic_index=self._partition_service.get_semantic_index(batch_working_set.partition),
        )

    @staticmethod
    def _collect_observed_profile_key_counts(*, cases: list[KnowbaseCaseDocument]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in cases:
            for key, raw_values in case.semantic_profile.ordered_items():
                normalized_key = str(key).strip()
                if not normalized_key or not raw_values:
                    continue
                counts[normalized_key] = counts.get(normalized_key, 0) + 1
        return counts

    @staticmethod
    def _collect_observed_facet_key_counts(*, cases: list[KnowbaseCaseDocument]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for case in cases:
            for key, raw_values in case.facets.ordered_items():
                normalized_key = str(key).strip()
                if not normalized_key or not raw_values:
                    continue
                counts[normalized_key] = counts.get(normalized_key, 0) + 1
        return counts

    @staticmethod
    def _collect_facet_index_key_counts(*, facet_index: PartitionFacetIndex | None) -> dict[str, int]:
        if facet_index is None:
            return {}
        counts: dict[str, int] = {}
        for item in facet_index.key_stats:
            normalized_key = item.key.strip()
            if normalized_key:
                counts[normalized_key] = int(item.count)
        return counts

    @staticmethod
    def _collect_index_key_counts(*, semantic_index: PartitionSemanticIndex | None) -> dict[str, int]:
        if semantic_index is None:
            return {}
        counts: dict[str, int] = {}
        for item in semantic_index.key_stats:
            normalized_key = item.key.strip()
            if normalized_key:
                counts[normalized_key] = int(item.count)
        return counts

    @staticmethod
    def _resolve_index_case_count(*, semantic_index: PartitionSemanticIndex | None) -> int:
        if semantic_index is None:
            return 0
        raw_case_count = semantic_index.metadata.get("case_count", 0)
        return int(raw_case_count) if isinstance(raw_case_count, (int, float, str)) else 0

    @staticmethod
    def _resolve_promotable_keys(
        *,
        existing_keys: list[str],
        index_key_counts: dict[str, int],
        index_case_count: int,
    ) -> list[str]:
        if index_case_count <= 0:
            return []
        threshold = max(2, int(index_case_count * 0.3))
        return sorted(key for key, count in index_key_counts.items() if key not in existing_keys and count >= threshold)

    @staticmethod
    def _resolve_demotable_keys(
        *,
        existing_keys: list[str],
        touched_keys: list[str],
        semantic_index_key_counts: dict[str, int],
        facet_index_key_counts: dict[str, int],
    ) -> list[str]:
        return sorted(
            key
            for key in existing_keys
            if (
                key not in touched_keys
                and semantic_index_key_counts.get(key, 0) == 0
                and facet_index_key_counts.get(key, 0) == 0
            )
        )

    @staticmethod
    def _resolve_coverage_score(
        *,
        sampled_case_ids: list[str],
        missing_key_signals: list[str],
        existing_keys: list[str],
        index_key_counts: dict[str, int],
        index_case_count: int,
    ) -> float:
        if not sampled_case_ids and not existing_keys and index_case_count <= 0:
            return 1.0
        score = 1.0
        if missing_key_signals:
            score -= min(0.4, 0.1 * len(missing_key_signals))
        if existing_keys:
            absent_keys = sum(1 for key in existing_keys if index_key_counts.get(key, 0) == 0)
            score -= min(0.3, 0.05 * absent_keys)
        if sampled_case_ids and not index_key_counts:
            score -= 0.2
        return max(0.0, round(score, 2))
