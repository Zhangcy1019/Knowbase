"""Tests for the read-only runtime stage of facet governance.

Run with:
    python3 -m unittest tests.unit.test_governance_runtime
"""

import asyncio
import unittest
from types import SimpleNamespace

from internal.knowledge.governance import (
    GovernanceRuntimeDecision,
    GovernanceRuntimeAgent,
    GovernanceService,
    PartitionFitMetrics,
)
from internal.knowledge.governance.models import (
    PartitionFacetCoverageAssessment,
    GovernanceRefreshScope,
)
from internal.knowledge.capability.skills.partition import ValidateGovernanceSkill
from internal.models.skill import SkillInvocation
from internal.models.skill import SkillResult
from internal.runtime.contracts import RuntimeRunResult
from internal.models.run import RunStep
from internal.knowledge.governance.validation import (
    GovernanceValidationContext,
    GovernanceValidationPipeline,
)
from internal.knowledge.governance.proposal import GovernanceProposalContext


class _ContextBuilder:
    def build_context(self, *, batch_working_set, statistics=None):
        del batch_working_set
        del statistics
        return SimpleNamespace(
            facet_coverage_assessment=PartitionFacetCoverageAssessment(partition="ci"),
            proposal_context=GovernanceProposalContext(
                partition="ci",
                scenario_description="",
                existing_facet_keys=[],
                observed_facet_keys=[],
                semantic_candidate_keys=[],
                missing_key_signals=[],
                stable_key_gaps=[],
                semantic_index_key_counts={"Area": 3},
                facet_index_key_counts={},
                semantic_index_case_count=3,
            ),
            refresh_scope=GovernanceRefreshScope(partition="ci"),
            notes=[],
        )


class _RuntimeAgent:
    async def decide(self, **kwargs):
        del kwargs
        return GovernanceRuntimeDecision(
            outcome="accepted",
            accepted_schema={"definitions": [{"key": "Area"}]},
            summary="Proposal is supported by the read-only evidence.",
        )


class _RuntimeWithRejectedValidation:
    async def run_request(self, *, request):
        del request
        return RuntimeRunResult(
            run_id="run-validation-rejected",
            status="requires_review",
            final_summary="validation skill budget exhausted",
            skill_results=[
                SkillResult(
                    skill_id="governance.validate_candidate",
                    ok=True,
                    output={
                        "passed": False,
                        "reasons": ["candidate coverage 0.00 is below 0.70"],
                        "plugins": [
                            {
                                "plugin": "fit_metrics",
                                "passed": False,
                                "reasons": ["candidate coverage 0.00 is below 0.70"],
                            }
                        ],
                    },
                )
            ],
        )


class _RuntimeWithPassedValidationBudgetStop:
    async def run_request(self, *, request):
        del request
        return RuntimeRunResult(
            run_id="run-validation-passed-budget-stop",
            status="failed",
            final_summary="run skill budget exceeded: 2>1",
            steps=[
                RunStep(
                    run_id="run-validation-passed-budget-stop",
                    step_type="action",
                    input={
                        "candidate_schema": {
                            "definitions": [
                                {
                                    "key": "causes",
                                    "display_name": "Causes",
                                    "description": "Root causes",
                                    "examples": ["network"],
                                    "enabled": True,
                                }
                            ],
                            "metadata": {"support_counts": {"causes": 2}, "source": "test"},
                        }
                    },
                    output={"capability_id": "governance.validate_candidate"},
                )
            ],
            skill_results=[
                SkillResult(
                    skill_id="governance.validate_candidate",
                    ok=True,
                    output={"passed": True, "reasons": [], "plugins": []},
                )
            ],
        )


class _RuntimeWithPassedValidationActionStop:
    async def run_request(self, *, request):
        del request
        return RuntimeRunResult(
            run_id="run-validation-passed-action-stop",
            status="requires_review",
            final_summary="No executable action left; must stop.",
            steps=[
                RunStep(
                    run_id="run-validation-passed-action-stop",
                    step_type="action",
                    input={
                        "candidate_schema": {
                            "definitions": [
                                {
                                    "key": "tools",
                                    "display_name": "Tools",
                                    "description": "Relevant tools",
                                    "examples": ["bazel"],
                                    "enabled": True,
                                }
                            ],
                            "metadata": {"source": "test"},
                        }
                    },
                    output={"capability_id": "governance.validate_candidate"},
                )
            ],
            skill_results=[
                SkillResult(
                    skill_id="governance.validate_candidate",
                    ok=True,
                    output={"passed": True, "reasons": [], "plugins": []},
                )
            ],
        )


class GovernanceRuntimeTest(unittest.TestCase):
    def test_passed_validation_recovers_from_duplicate_skill_budget_stop(self):
        agent = GovernanceRuntimeAgent(runtime=_RuntimeWithPassedValidationBudgetStop())

        result = asyncio.run(
            agent.decide(
                partition="ci",
                statistics={},
                current_schema={"definitions": []},
                working_set=SimpleNamespace(metadata={}),
                evidence={},
            )
        )

        self.assertEqual(result.outcome, "accepted")
        self.assertEqual(result.accepted_schema.definitions[0].key, "causes")
        self.assertEqual(result.metadata["decision_source"], "validated_candidate_recovery")

    def test_passed_validation_recovers_from_no_executable_action_stop(self):
        agent = GovernanceRuntimeAgent(runtime=_RuntimeWithPassedValidationActionStop())

        result = asyncio.run(
            agent.decide(
                partition="ci",
                statistics={},
                current_schema={"definitions": []},
                working_set=SimpleNamespace(metadata={}),
                evidence={},
            )
        )

        self.assertEqual(result.outcome, "accepted")
        self.assertEqual(result.accepted_schema.definitions[0].key, "tools")
        self.assertEqual(result.metadata["decision_source"], "validated_candidate_recovery")

    def test_rejected_validation_is_not_promoted_to_manual_review(self):
        agent = GovernanceRuntimeAgent(runtime=_RuntimeWithRejectedValidation())

        result = asyncio.run(
            agent.decide(
                partition="ci",
                statistics={},
                current_schema={"definitions": []},
                working_set=SimpleNamespace(metadata={}),
                evidence={},
            )
        )

        self.assertEqual(result.outcome, "no_change")
        self.assertFalse(result.metadata["validation"]["passed"])
        self.assertEqual(result.metadata["decision_source"], "deterministic_validation")
        self.assertIn("candidate coverage", result.reasons[0])

    def test_runtime_decision_can_accept_candidate_without_mutating(self):
        service = GovernanceService(
            context_builder=_ContextBuilder(),
            decision_agent=_RuntimeAgent(),
            fit_metrics=PartitionFitMetrics(),
        )
        result = asyncio.run(
            service.assess_async(
                statistics={"case_count": 3, "case_key_stats": {"Area": 3}},
                current_schema={"definitions": []},
                working_set=SimpleNamespace(partition="ci", affected_case_ids=[]),
            )
        )

        self.assertEqual(result.decision, "accepted")
        self.assertFalse(result.requires_review)
        self.assertEqual(result.accepted_schema.definitions[0].key, "Area")

    def test_runtime_decision_requires_complete_schema_when_accepted(self):
        result = GovernanceRuntimeAgent._parse_decision(
            decision_payload={"outcome": "accepted", "summary": "accepted", "reasons": []},
            run_id="run-1",
        )

        self.assertEqual(result.outcome, "requires_review")
        self.assertIn("accepted_schema must be an object when outcome is accepted", result.reasons)

    def test_runtime_decision_rejects_invalid_complete_schema(self):
        result = GovernanceRuntimeAgent._parse_decision(
            decision_payload={
                "outcome": "accepted",
                "summary": "change",
                "reasons": [],
                "accepted_schema": {"definitions": [{"key": "Area"}]},
            },
            run_id="run-1",
        )

        self.assertEqual(result.outcome, "requires_review")
        self.assertTrue(result.reasons)

    def test_validation_pipeline_runs_only_registered_fit_plugin(self):
        report = GovernanceValidationPipeline(
            plugins=[PartitionFitMetrics()]
        ).validate(
            context=GovernanceValidationContext(
                partition="ci",
                statistics={"case_count": 3, "case_key_stats": {"Area": 3}},
                current_schema={"definitions": []},
                candidate_schema={"definitions": [{"key": "Area"}]},
            )
        )

        self.assertTrue(report.passed)
        self.assertEqual([item.plugin for item in report.results], ["fit_metrics"])

    def test_validation_pipeline_collects_all_plugin_results_after_failure(self):
        class _Plugin:
            def __init__(self, name, error=False):
                self.name = name
                self.error = error

            def validate(self, *, context):
                _ = context
                if self.error:
                    raise RuntimeError("broken validator")
                from internal.knowledge.governance.validation import GovernanceValidationResult

                return GovernanceValidationResult(plugin=self.name, passed=True)

        report = GovernanceValidationPipeline(
            plugins=[_Plugin("first"), _Plugin("broken", error=True), _Plugin("third")]
        ).validate(
            context=GovernanceValidationContext(
                partition="ci",
                statistics={},
                current_schema={},
                candidate_schema={},
            )
        )

        self.assertFalse(report.passed)
        self.assertEqual([item.plugin for item in report.results], ["first", "broken", "third"])

    def test_runtime_validation_skill_returns_complete_pipeline_report(self):
        skill = ValidateGovernanceSkill(
            validation_pipeline=GovernanceValidationPipeline(plugins=[PartitionFitMetrics()])
        )
        result = skill.execute(
            SkillInvocation(
                invocation_id="validation-1",
                skill_id="governance.validate_candidate",
                partition="ci",
                inputs={
                    "partition": "ci",
                    "current_schema": {"definitions": []},
                    "candidate_schema": {"definitions": [{"key": "Area"}]},
                    "semantic_key_counts": {"Area": 3},
                    "case_count": 3,
                },
            )
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.output["passed"])
        self.assertEqual([item["plugin"] for item in result.output["plugins"]], ["fit_metrics"])

    def test_runtime_validation_normalizes_statistics_namespace(self):
        skill = ValidateGovernanceSkill(
            validation_pipeline=GovernanceValidationPipeline(plugins=[PartitionFitMetrics()])
        )
        result = skill.execute(
            SkillInvocation(
                invocation_id="validation-namespaced-1",
                skill_id="governance.validate_candidate",
                partition="ci",
                inputs={
                    "partition": "ci",
                    "current_schema": {"definitions": []},
                    "candidate_schema": {"definitions": [{"key": "Area"}]},
                    "semantic_key_counts": {"semantic_profile:Area": 3},
                    "case_count": 3,
                },
            )
        )

        self.assertTrue(result.ok)
        self.assertTrue(result.output["passed"])


if __name__ == "__main__":
    unittest.main()
