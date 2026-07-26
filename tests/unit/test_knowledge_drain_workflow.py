"""Knowledge drain workflow unit tests."""

import asyncio
from types import SimpleNamespace
import unittest

from internal.backlog.events.models import BacklogBatch
from internal.knowledge.facet_governance.models import (
    FacetGovernanceResult,
    PartitionFacetSchemaProposal,
    PartitionRebuildRecommendation,
)
from internal.knowledge.projection.models import CaseProjectionChange, ProjectionPlan
from internal.knowledge.workflow import KnowledgeDrainWorkflow


class _Governance:
    def __init__(self, result) -> None:
        self.result = result
        self.current_schema = None

    def assess(self, *, statistics, current_schema, working_set):
        self.current_schema = current_schema
        return self.result


class _PartitionService:
    def get_facet_schema(self, partition):
        return {"partition": partition}


class _Projection:
    def plan(self, *, partition, accepted_schema, case_ids):
        return ProjectionPlan(
            partition=partition,
            target_case_ids=case_ids,
            changes=[
                CaseProjectionChange(
                    partition=partition,
                    case_id="case-1",
                    before_facets={"Area": ["Old"]},
                    after_facets={"Area": ["Build"]},
                )
            ],
        )


class _Executor:
    def __init__(self) -> None:
        self.plan = None

    def apply(self, *, plan):
        self.plan = plan
        return SimpleNamespace(updated_paths=["cases/case-1.json"], updated_case_ids=["case-1"])

    @staticmethod
    def planned_paths(*, plan):
        return [f"cases/{change.case_id}.json" for change in plan.case_changes]


class KnowledgeDrainWorkflowTest(unittest.TestCase):
    def _batch(self) -> BacklogBatch:
        return BacklogBatch(batch_id="batch-1", partition="ci")

    def test_accepted_governance_applies_mutation_without_runtime(self) -> None:
        governance = _Governance(
            FacetGovernanceResult(
                decision="accepted",
                accepted_schema={"definitions": []},
                proposal=PartitionFacetSchemaProposal(
                    partition="ci", suggested_new_keys=["Area"]
                ),
                rebuild=PartitionRebuildRecommendation(
                    partition="ci",
                    rebuild_scope="partial",
                    target_case_ids=["case-1"],
                ),
            )
        )
        executor = _Executor()
        workflow = KnowledgeDrainWorkflow(
            facet_governance=governance,
            partition_service=_PartitionService(),
            projection=_Projection(),
            mutation_executor=executor,
        )

        result = asyncio.run(workflow.run_batch(batch=self._batch()))

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.applied_case_ids, ["case-1"])
        self.assertIsNotNone(executor.plan)
        self.assertEqual(executor.plan.case_changes[0].case_id, "case-1")
        self.assertEqual(governance.current_schema, {"partition": "ci"})

    def test_rejected_governance_does_not_write(self) -> None:
        executor = _Executor()
        workflow = KnowledgeDrainWorkflow(
            facet_governance=_Governance(
                FacetGovernanceResult(decision="rejected", reasons=["insufficient support"])
            ),
            mutation_executor=executor,
        )

        result = asyncio.run(workflow.run_batch(batch=self._batch()))

        self.assertEqual(result.status, "completed")
        self.assertIsNone(executor.plan)


if __name__ == "__main__":
    unittest.main()
