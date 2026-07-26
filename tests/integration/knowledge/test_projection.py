"""Projection integration tests.

Run:
    cd /home/zcy/Project/knowbase
    python3 -m unittest tests.integration.knowledge.test_projection
"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from internal.infrastructure.persistence.local import KnowbaseCaseRepository
from internal.knowledge.projection import (
    CaseFacetProjector,
    KnowledgeProjectionService,
)
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.models import (
    CaseFacetProfile,
    CaseSemanticProfile,
    KnowbaseCaseDocument,
    KnowbaseCaseMetadata,
    PartitionFacetDefinition,
    PartitionFacetSchema,
)


class ProjectionIntegrationTest(unittest.TestCase):
    def _build_service(self, root: Path) -> KnowledgeProjectionService:
        return KnowledgeProjectionService(
            case_repository=KnowbaseCaseRepository(root=root),
            projector=CaseFacetProjector(facet_resolver=KnowbaseCaseFacetResolver()),
        )

    @staticmethod
    def _case(*, case_id: str, partition: str = "ci", facets=None) -> KnowbaseCaseDocument:
        now = datetime.now(timezone.utc)
        return KnowbaseCaseDocument(
            case_id=case_id,
            partition=partition,
            created_at=now,
            updated_at=now,
            metadata=KnowbaseCaseMetadata(),
            title="Build issue",
            source_content="Buildbarn access fails.",
            semantic_profile=CaseSemanticProfile(
                Area=["Build"],
                Environment=["Guangzhou"],
            ),
            facets=CaseFacetProfile.model_validate(facets or {"Area": ["Old"]}),
        )

    def test_projection_returns_before_after_changes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = KnowbaseCaseRepository(root=root)
            repository.upsert(self._case(case_id="case-1"))
            service = self._build_service(root)
            schema = PartitionFacetSchema(
                definitions=[
                    PartitionFacetDefinition(key="Area"),
                    PartitionFacetDefinition(key="Environment"),
                ]
            )

            plan = service.plan(
                partition="ci",
                accepted_schema=schema,
                case_ids=["case-1"],
            )

            self.assertEqual(plan.estimated_change_count, 1)
            self.assertEqual(plan.changes[0].before_facets, {"Area": ["Old"]})
            self.assertEqual(
                plan.changes[0].after_facets,
                {"Area": ["Build"], "Environment": ["Guangzhou"]},
            )
            self.assertEqual(plan.changes[0].changed_keys, ["Area", "Environment"])

    def test_projection_classifies_unchanged_missing_and_wrong_partition_cases(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repository = KnowbaseCaseRepository(root=root)
            repository.upsert(
                self._case(
                    case_id="case-unchanged",
                    facets={"Area": ["Build"], "Environment": ["Guangzhou"]},
                )
            )
            repository.upsert(self._case(case_id="case-other", partition="prod"))
            service = self._build_service(root)
            schema = PartitionFacetSchema(
                definitions=[
                    PartitionFacetDefinition(key="Area"),
                    PartitionFacetDefinition(key="Environment"),
                ]
            )

            plan = service.plan(
                partition="ci",
                accepted_schema=schema,
                case_ids=["case-unchanged", "case-other", "case-missing"],
            )

            self.assertEqual(plan.unchanged_case_ids, ["case-unchanged"])
            self.assertEqual(plan.skipped_case_ids, ["case-other", "case-missing"])
            self.assertEqual(plan.changes, [])


if __name__ == "__main__":
    unittest.main()
