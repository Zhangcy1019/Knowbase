"""Knowledge mutation-plan unit tests."""

from types import SimpleNamespace
import unittest

from internal.knowledge.model import KnowledgeMutationPlan
from internal.knowledge.projection.models import CaseProjectionChange, ProjectionPlan


class KnowledgeMutationPlanTest(unittest.TestCase):
    def test_from_governance_combines_accepted_schema_and_projection(self) -> None:
        schema = object()
        governance = SimpleNamespace(
            risk_level="low",
            accepted_schema=schema,
            reasons=["stable support"],
            proposal=SimpleNamespace(suggested_new_keys=["Area"]),
        )
        projection = ProjectionPlan(
            partition="ci",
            changes=[
                CaseProjectionChange(
                    partition="ci",
                    case_id="case-1",
                    before_facets={"Area": ["Old"]},
                    after_facets={"Area": ["Build"]},
                )
            ],
        )

        plan = KnowledgeMutationPlan.from_governance(
            batch=SimpleNamespace(batch_id="batch-1", partition="ci"),
            governance=governance,
            projection=projection,
        )

        self.assertTrue(plan.plan_id.startswith("mutation-"))
        self.assertEqual(plan.partition, "ci")
        self.assertIs(plan.accepted_schema, schema)
        self.assertEqual(plan.affected_case_ids, ["case-1"])


if __name__ == "__main__":
    unittest.main()
