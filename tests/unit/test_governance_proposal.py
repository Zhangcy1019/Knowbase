"""Tests for pluggable deterministic schema-proposal discovery.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.unit.test_governance_proposal
"""

import unittest

from internal.knowledge.governance.proposal import (
    FacetKeyDemotionProposal,
    GovernanceProposalContext,
    GovernanceProposalPluginResult,
    GovernanceProposalPipeline,
    SemanticKeyPromotionProposal,
)


class GovernanceProposalPipelineTest(unittest.TestCase):
    def _context(self) -> GovernanceProposalContext:
        return GovernanceProposalContext(
            partition="CI",
            scenario_description="",
            existing_facet_keys=["owner", "obsolete"],
            observed_facet_keys=["owner"],
            semantic_candidate_keys=[],
            missing_key_signals=["case-1:missing-facet"],
            stable_key_gaps=[],
            semantic_index_key_counts={"owner": 8, "domain": 4},
            facet_index_key_counts={"owner": 5},
            semantic_index_case_count=10,
        )

    def test_plugins_contribute_independent_candidates(self) -> None:
        report = GovernanceProposalPipeline(
            plugins=[
                SemanticKeyPromotionProposal(),
                FacetKeyDemotionProposal(),
            ]
        ).propose(context=self._context())

        self.assertTrue(report.has_effective_proposal)
        self.assertEqual(report.proposal.suggested_new_keys, ["domain"])
        self.assertEqual(report.proposal.suggested_removed_keys, ["obsolete"])
        self.assertEqual(len(report.results), 2)
        promotion, demotion = report.results
        self.assertIn("absent from the current facet schema", promotion.root_cause)
        self.assertEqual(promotion.evidence["candidate_support_counts"], {"domain": 4})
        self.assertEqual(promotion.evidence["promotion_threshold"], 3)
        self.assertIn("zero semantic-index and facet-index support", demotion.reasons[0])
        self.assertEqual(demotion.evidence["candidate_support"]["obsolete"]["semantic_index_count"], 0)

    def test_empty_pipeline_does_not_create_effective_proposal(self) -> None:
        report = GovernanceProposalPipeline().propose(context=self._context())

        self.assertFalse(report.has_effective_proposal)
        self.assertEqual(report.proposal.suggested_new_keys, [])
        self.assertEqual(report.results, [])

    def test_snapshot_statistics_drive_promotion_threshold(self) -> None:
        context = GovernanceProposalContext(
            partition="CI",
            scenario_description="",
            existing_facet_keys=[],
            observed_facet_keys=[],
            semantic_candidate_keys=[],
            missing_key_signals=[],
            stable_key_gaps=[],
            # Stale materialized index values intentionally disagree.
            semantic_index_key_counts={"domain": 1},
            facet_index_key_counts={},
            semantic_index_case_count=100,
            statistics_case_count=10,
            statistics_semantic_key_counts={"domain": 4},
            statistics_facet_key_counts={},
            consistency_status="consistent",
        )

        result = SemanticKeyPromotionProposal().propose(context=context)

        self.assertEqual(result.suggested_new_keys, ["domain"])
        self.assertEqual(result.evidence["statistics_case_count"], 10)
        self.assertEqual(result.evidence["promotion_threshold"], 3)

    def test_promotion_is_conservative_and_excludes_semantic_only_fields(self) -> None:
        context = GovernanceProposalContext(
            partition="CI",
            scenario_description="",
            existing_facet_keys=[],
            observed_facet_keys=[],
            semantic_candidate_keys=[],
            missing_key_signals=[],
            stable_key_gaps=[],
            semantic_index_key_counts={},
            facet_index_key_counts={},
            semantic_index_case_count=2,
            statistics_case_count=2,
            statistics_semantic_key_counts={
                "actions": 2,
                "causes": 2,
                "components": 2,
                "doc_type": 2,
                "keywords": 2,
                "symptoms": 2,
                "title": 2,
            },
        )

        result = SemanticKeyPromotionProposal().propose(context=context)

        self.assertEqual(result.suggested_new_keys, ["causes", "components"])
        self.assertEqual(result.metrics["max_new_keys"], 2)
        self.assertEqual(result.evidence["excluded_semantic_keys"], ["actions", "keywords", "title"])
        self.assertEqual(result.evidence["limited_semantic_keys"], ["doc_type", "symptoms"])
        self.assertTrue(any("retained as semantic-only" in reason for reason in result.reasons))
        self.assertTrue(any("per-drain new-key limit" in reason for reason in result.reasons))

    def test_pipeline_preserves_conflicting_actions_for_runtime(self) -> None:
        class _Add:
            name = "add"

            def propose(self, *, context):
                del context
                return GovernanceProposalPluginResult(
                    plugin=self.name,
                    suggested_new_keys=["region"],
                    root_cause="new key candidate",
                )

        class _Remove:
            name = "remove"

            def propose(self, *, context):
                del context
                return GovernanceProposalPluginResult(
                    plugin=self.name,
                    suggested_removed_keys=["region"],
                    root_cause="remove key candidate",
                )

        report = GovernanceProposalPipeline(plugins=[_Add(), _Remove()]).propose(context=self._context())

        self.assertEqual(report.status, "proposed")
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(report.conflicts[0].key, "region")
        self.assertEqual(report.impact["conflict_count"], 1)
        self.assertEqual(report.reason_details[-1]["code"], "proposal_conflict")

    def test_pipeline_blocks_inconsistent_evidence(self) -> None:
        context = self._context().model_copy(
            update={
                "consistency_status": "inconsistent",
                "consistency_mismatches": [{"kind": "case_count_mismatch"}],
            }
        )

        report = GovernanceProposalPipeline(plugins=[SemanticKeyPromotionProposal()]).propose(context=context)

        self.assertEqual(report.status, "blocked")
        self.assertFalse(report.has_effective_proposal)
        self.assertEqual(report.reason_details[0]["code"], "proposal_blocked_by_evidence_consistency")


if __name__ == "__main__":
    unittest.main()
