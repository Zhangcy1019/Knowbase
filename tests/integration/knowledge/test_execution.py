"""Knowledge mutation execution integration tests.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.integration.knowledge.test_execution
"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from internal.infrastructure.persistence.local import KnowbaseCaseRepository
from internal.knowledge.execution import KnowledgeMutationExecutor
from internal.knowledge.model.mutation_plan import KnowledgeMutationPlan
from internal.knowledge.projection.models import CaseProjectionChange
from internal.models import (
    CaseFacetProfile,
    CaseSemanticProfile,
    KnowbaseCaseDocument,
    KnowbaseCaseMetadata,
    PartitionFacetDefinition,
    PartitionFacetSchema,
)


class _PartitionServiceStub:
    def __init__(self) -> None:
        self.saved: list[tuple[str, PartitionFacetSchema]] = []

    def save_facet_schema(self, *, partition_name: str, facet_schema: PartitionFacetSchema):
        self.saved.append((partition_name, facet_schema))
        return facet_schema


class KnowledgeMutationExecutorIntegrationTest(unittest.TestCase):
    @staticmethod
    def _case(case_id: str) -> KnowbaseCaseDocument:
        now = datetime.now(timezone.utc)
        return KnowbaseCaseDocument(
            case_id=case_id,
            partition="ci",
            created_at=now,
            updated_at=now,
            metadata=KnowbaseCaseMetadata(),
            title="Build issue",
            source_content="Buildbarn access fails.",
            semantic_profile=CaseSemanticProfile(Area=["Build"]),
            facets=CaseFacetProfile(Area=["Old"]),
        )

    def test_apply_updates_case_and_schema_and_returns_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = KnowbaseCaseRepository(root=root)
            repository.upsert(self._case("case-1"))
            now = datetime.now(timezone.utc)
            partition_service = _PartitionServiceStub()
            schema = PartitionFacetSchema(
                definitions=[PartitionFacetDefinition(key="Area")]
            )
            plan = KnowledgeMutationPlan(
                plan_id="mutation-1",
                partition="ci",
                batch_id="batch-1",
                created_at=now.isoformat(),
                accepted_schema=schema,
                case_changes=[
                    CaseProjectionChange(
                        case_id="case-1",
                        partition="ci",
                        before_facets={"Area": ["Old"]},
                        after_facets={"Area": ["Build"]},
                    )
                ],
            )

            result = KnowledgeMutationExecutor(
                case_repository=repository,
                partition_service=partition_service,
            ).apply(plan=plan)

            self.assertEqual(result.plan_id, "mutation-1")
            self.assertEqual(result.updated_case_ids, ["case-1"])
            self.assertEqual(
                result.updated_paths,
                ["cases/case-1.json", "partition_facet_schemas/ci.json"],
            )
            self.assertEqual(repository.get("case-1").facets.model_dump(), {"Area": ["Build"]})
            self.assertEqual(partition_service.saved, [("ci", schema)])

    def test_apply_fails_before_writing_when_case_is_missing(self) -> None:
        with TemporaryDirectory() as directory:
            repository = KnowbaseCaseRepository(root=Path(directory))
            plan = KnowledgeMutationPlan(
                plan_id="mutation-missing",
                partition="ci",
                batch_id="batch-1",
                created_at=datetime.now(timezone.utc).isoformat(),
                case_changes=[
                    CaseProjectionChange(
                        case_id="missing",
                        partition="ci",
                        before_facets={},
                        after_facets={"Area": ["Build"]},
                    )
                ],
            )

            with self.assertRaisesRegex(ValueError, "case not found"):
                KnowledgeMutationExecutor(case_repository=repository).apply(plan=plan)

    def test_preflight_failure_does_not_write_schema_or_other_cases(self) -> None:
        with TemporaryDirectory() as directory:
            repository = KnowbaseCaseRepository(root=Path(directory))
            repository.upsert(self._case("case-1"))
            partition_service = _PartitionServiceStub()
            plan = KnowledgeMutationPlan(
                plan_id="mutation-preflight",
                batch_id="batch-1",
                partition="ci",
                created_at=datetime.now(timezone.utc).isoformat(),
                accepted_schema=PartitionFacetSchema(
                    definitions=[PartitionFacetDefinition(key="Area")]
                ),
                case_changes=[
                    CaseProjectionChange(
                        case_id="case-1",
                        partition="ci",
                        before_facets={"Area": ["Old"]},
                        after_facets={"Area": ["Build"]},
                    ),
                    CaseProjectionChange(
                        case_id="missing",
                        partition="ci",
                        before_facets={},
                        after_facets={"Area": ["Build"]},
                    ),
                ],
            )

            with self.assertRaisesRegex(ValueError, "case not found"):
                KnowledgeMutationExecutor(
                    case_repository=repository,
                    partition_service=partition_service,
                ).apply(plan=plan)

            self.assertEqual(repository.get("case-1").facets.model_dump(), {"Area": ["Old"]})
            self.assertEqual(partition_service.saved, [])


if __name__ == "__main__":
    unittest.main()
