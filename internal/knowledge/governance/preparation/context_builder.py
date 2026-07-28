"""Compose batch working-set resources into governance preparation."""

from __future__ import annotations

from internal.knowledge.batch.models import BatchWorkingSet
from internal.knowledge.governance.preparation.coverage import CoverageEvaluator
from internal.knowledge.governance.preparation.evidence import (
    GovernanceEvidenceLoader,
    GovernanceSignalCollector,
)
from internal.knowledge.governance.preparation.models import GovernancePreparation
from internal.knowledge.governance.proposal import GovernanceProposalContext
from internal.ports import CaseReadPort, PartitionProfileReadPort, PartitionReadPort
from internal.knowledge.governance.preparation.models import GovernanceRefreshScope


def _build_refresh_scope(
    *,
    batch_working_set: BatchWorkingSet,
    signals,
) -> GovernanceRefreshScope:
    affected_case_ids = signals.affected_case_ids
    return GovernanceRefreshScope(
        partition=batch_working_set.partition,
        scope="affected_cases" if affected_case_ids else "none",
        case_ids=affected_case_ids,
        facet_keys=list(dict.fromkeys(signals.observed_facet_keys)),
        reason="Recent case updates may require recomputing case facets under the current partition schema.",
    )


class GovernanceContextBuilder:
    """Orchestrate preparation without making schema decisions or mutations."""

    def __init__(
        self,
        *,
        partition_service: PartitionReadPort | PartitionProfileReadPort,
        case_repository: CaseReadPort,
        evidence_loader: GovernanceEvidenceLoader | None = None,
        signal_collector: GovernanceSignalCollector | None = None,
        coverage_evaluator: CoverageEvaluator | None = None,
    ):
        self._evidence_loader = evidence_loader or GovernanceEvidenceLoader(
            partition_service=partition_service,
            case_repository=case_repository,
        )
        self._signal_collector = signal_collector or GovernanceSignalCollector()
        self._coverage_evaluator = coverage_evaluator or CoverageEvaluator()

    def build_context(self, *, batch_working_set: BatchWorkingSet, statistics=None) -> GovernancePreparation:
        # inputs: GovernanceEvidenceInputs
        inputs = self._evidence_loader.load(
            batch_working_set=batch_working_set,
            statistics=statistics,
        )
        signals = self._signal_collector.collect(
            batch_working_set=batch_working_set,
            inputs=inputs,
        )
        coverage = self._coverage_evaluator.evaluate(
            batch_working_set=batch_working_set,
            inputs=inputs,
            signals=signals,
        )
        refresh_scope = _build_refresh_scope(
            batch_working_set=batch_working_set,
            signals=signals,
        )
        proposal_context = GovernanceProposalContext(
            partition=batch_working_set.partition,
            scenario_description=inputs.partition_scenario_description,
            existing_facet_keys=signals.existing_facet_keys,
            observed_facet_keys=signals.observed_facet_keys,
            semantic_candidate_keys=signals.semantic_candidate_keys,
            missing_key_signals=signals.missing_key_signals,
            stable_key_gaps=signals.stable_key_gaps,
            semantic_index_key_counts=signals.semantic_index_key_counts,
            facet_index_key_counts=signals.facet_index_key_counts,
            semantic_index_case_count=signals.semantic_index_case_count,
            statistics_case_count=signals.statistics_case_count,
            statistics_semantic_key_counts=signals.statistics_semantic_key_counts,
            statistics_facet_key_counts=signals.statistics_facet_key_counts,
            consistency_status=signals.consistency_status,
            consistency_mismatches=signals.consistency_mismatches,
            affected_case_count=len(signals.affected_case_ids),
        )
        return GovernancePreparation(
            summary=f"Prepared batch {batch_working_set.batch_id} with a deterministic refresh scope.",
            risk_level="medium" if refresh_scope.case_ids or signals.missing_key_signals else "low",
            consistency_status=signals.consistency_status,
            consistency_mismatches=signals.consistency_mismatches,
            facet_coverage_assessment=coverage,
            proposal_context=proposal_context,
            refresh_scope=refresh_scope,
            notes=[
                "Preparation planning focuses on evidence collection, coverage assessment, and affected-case refresh planning.",
                f"resource_group_count={len(batch_working_set.resource_groups)}",
                f"loaded_case_count={len(inputs.affected_cases)}",
                f"statistics_case_count={signals.statistics_case_count}",
                f"evidence_consistency={signals.consistency_status}",
            ],
        )


__all__ = ["GovernanceContextBuilder"]
