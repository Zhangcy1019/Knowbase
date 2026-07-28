"""Deterministic facet governance tests.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.unit.test_governance
"""

from types import SimpleNamespace
import unittest

from internal.knowledge.governance import (
    GovernanceService,
    GovernancePreparation,
    PartitionFitMetrics,
)
from internal.knowledge.governance.proposal import GovernanceProposalContext
from internal.models import PartitionFacetDefinition, PartitionFacetSchema
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticKeyStat


class _ContextBuilder:
    def __init__(self, preparation: GovernancePreparation):
        self.preparation = preparation

    def build_context(self, *, batch_working_set, statistics=None):
        _ = batch_working_set
        _ = statistics
        return self.preparation


class GovernanceServiceTest(unittest.TestCase):
    def _working_set(self, case_ids=None):
        return SimpleNamespace(
            partition="CI",
            affected_case_ids=case_ids or [],
                observed_facet_keys=[],
        )

    def test_accepts_current_schema_when_preparation_has_no_schema_proposal(self) -> None:
        current_schema = PartitionFacetSchema()
        service = GovernanceService(
            context_builder=_ContextBuilder(GovernancePreparation()),
        )

        result = service.assess_deterministic(
            statistics={"case_count": 2},
            current_schema=current_schema,
            working_set=self._working_set(["case-1"]),
        )

        self.assertEqual(result.decision, "no_change")
        self.assertFalse(result.requires_review)
        self.assertIs(result.accepted_schema, current_schema)
        self.assertIsNotNone(result.evidence)
        self.assertEqual(result.evidence.statistics_summary["case_count"], 2)

    def test_requires_review_when_schema_candidates_need_a_decision_agent(self) -> None:
        preparation = GovernancePreparation(
            proposal_context=GovernanceProposalContext(
                partition="CI",
                scenario_description="",
                existing_facet_keys=[],
                observed_facet_keys=[],
                semantic_candidate_keys=[],
                missing_key_signals=[],
                stable_key_gaps=[],
                semantic_index_key_counts={"domain": 3},
                facet_index_key_counts={},
                semantic_index_case_count=3,
            )
        )
        service = GovernanceService(
            context_builder=_ContextBuilder(preparation),
        )

        result = service.assess_deterministic(
            statistics=None,
            current_schema=PartitionFacetSchema(),
            working_set=self._working_set(["case-1"]),
        )

        self.assertEqual(result.decision, "requires_review")
        self.assertTrue(result.requires_review)
        self.assertIn("decision agent", " ".join(result.reasons))

    def test_only_registered_validation_plugins_are_active(self) -> None:
        service = GovernanceService(
            context_builder=_ContextBuilder(GovernancePreparation()),
        )

        result = service.assess_deterministic(
            statistics=None,
            current_schema=PartitionFacetSchema(),
            working_set=self._working_set(["case-1", "case-2"]),
        )

        self.assertEqual(result.decision, "no_change")
        self.assertFalse(result.requires_review)

    def test_fit_metrics_reports_unobserved_existing_keys(self) -> None:
        result = PartitionFitMetrics().evaluate(
            partition="CI",
            semantic_index=PartitionSemanticIndex(
                partition_name="CI",
                metadata={"case_count": 3},
                key_stats=[PartitionSemanticKeyStat(key="domain", count=3)],
            ),
            schema=PartitionFacetSchema(
                definitions=[
                    PartitionFacetDefinition(key="domain"),
                    PartitionFacetDefinition(key="source_kind"),
                ]
            ),
        )

        self.assertEqual(result["coverage_score"], 0.5)
        self.assertEqual(result["unobserved_existing_keys"], ["source_kind"])

    def test_fit_metrics_rejects_weak_new_key_support(self) -> None:
        result = PartitionFitMetrics().evaluate_candidate(
            partition="CI",
            current_schema={"definitions": [{"key": "domain"}]},
            candidate_schema={"definitions": [{"key": "domain"}, {"key": "rare"}]},
            semantic_key_counts={"domain": 10, "rare": 1},
            case_count=10,
        )

        self.assertFalse(result["passed"])
        self.assertEqual(result["weak_new_keys"], ["rare"])


if __name__ == "__main__":
    unittest.main()
