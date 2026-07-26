"""Local persistence repository integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.infrastructure.persistence.local.test_local_repositories
"""

from __future__ import annotations

import shutil
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from internal.infrastructure.persistence.local import build_local_persistence_bundle
from internal.models import (
    AgentRun,
    CaseFacetProfile,
    CaseSemanticProfile,
    EventRecord,
    KnowbaseCaseDocument,
    KnowbaseCaseSearchQuery,
    PartitionDocument,
    PartitionFacetDefinition,
    PartitionFacetIndex,
    PartitionFacetIndexDocument,
    PartitionFacetKeyStat,
    PartitionFacetSchema,
    PartitionFacetSchemaDocument,
    PartitionFacetValueStat,
    PartitionSemanticIndex,
    PartitionSemanticIndexDocument,
    PartitionSemanticKeyStat,
    PartitionSemanticValueStat,
    RunArtifact,
    RunStep,
)
from internal.models.events import CaseEventPayload
from tests.integration.support import load_test_runtime_config


class LocalRepositoriesIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._runtime_cfg = load_test_runtime_config()
        self._root = Path(self._runtime_cfg.storage.local_root).expanduser()
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)
        self._bundle = build_local_persistence_bundle(runtime_cfg=self._runtime_cfg)

    def tearDown(self) -> None:
        pass

    def test_build_bundle_and_partition_profile_repositories_round_trip(self) -> None:
        now = datetime.now(timezone.utc)

        partition = self._bundle.partition_repository.upsert(
            PartitionDocument(
                partition_name="CI",
                scenario_description="Claims and tax operations",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        schema = self._bundle.partition_facet_schema_repository.upsert(
            PartitionFacetSchemaDocument(
                partition_name="CI",
                facet_schema=PartitionFacetSchema(
                    definitions=[
                        PartitionFacetDefinition(
                            key="domain",
                            display_name="Domain",
                            description="Top-level domain",
                        )
                    ],
                    metadata={"schema_version": 1},
                ),
                created_at=now,
                updated_at=now,
            )
        )
        facet_index = self._bundle.partition_facet_index_repository.upsert(
            PartitionFacetIndexDocument(
                partition_name="CI",
                facet_index=PartitionFacetIndex(
                    partition_name="CI",
                    key_stats=[
                        PartitionFacetKeyStat(
                            key="domain",
                            count=2,
                            sample_values=[PartitionFacetValueStat(value="tax", count=1)],
                            last_seen_at=now,
                        )
                    ],
                    metadata={"case_count": 2},
                ),
                created_at=now,
                updated_at=now,
            )
        )
        semantic_index = self._bundle.partition_semantic_index_repository.upsert(
            PartitionSemanticIndexDocument(
                partition_name="CI",
                semantic_index=PartitionSemanticIndex(
                    partition_name="CI",
                    key_stats=[
                        PartitionSemanticKeyStat(
                            key="topic",
                            count=2,
                            sample_values=[PartitionSemanticValueStat(value="policy", count=2)],
                            aliases=["subject"],
                            last_seen_at=now,
                        )
                    ],
                    metadata={"case_count": 2},
                ),
                created_at=now,
                updated_at=now,
            )
        )

        self.assertEqual(partition.partition_name, "CI")
        self.assertEqual(
            self._bundle.partition_repository.get("CI").scenario_description,
            "Claims and tax operations",
        )
        self.assertEqual(len(self._bundle.partition_repository.list_documents()), 1)
        self.assertEqual(schema.facet_schema.definitions[0].key, "domain")
        self.assertEqual(
            self._bundle.partition_facet_schema_repository.get("CI").facet_schema.metadata["schema_version"],
            1,
        )
        self.assertEqual(facet_index.facet_index.key_stats[0].sample_values[0].value, "tax")
        self.assertEqual(semantic_index.semantic_index.key_stats[0].aliases, ["subject"])

        self.assertTrue((self._root / "partitions" / "CI.json").exists())
        self.assertTrue((self._root / "partitions" / "CI" / "facet_schema.json").exists())
        self.assertTrue((self._root / "partitions" / "CI" / "facet_index.json").exists())
        self.assertTrue((self._root / "partitions" / "CI" / "semantic_index.json").exists())

    def test_case_repository_supports_partition_listing_and_search(self) -> None:
        now = datetime.now(timezone.utc)
        older = now - timedelta(minutes=5)
        tax_case = self._bundle.case_repository.upsert(
            KnowbaseCaseDocument(
                case_id="case-tax-1",
                partition="CI",
                created_at=older,
                updated_at=older,
                title="Tax policy memo",
                source_content="Tax policy memo for integration testing.",
                summary_text="Tax policy summary",
                semantic_profile=CaseSemanticProfile.model_validate({"topic": ["policy"]}),
                facets=CaseFacetProfile.model_validate({"domain": ["tax"]}),
                search_text="tax policy memo domain tax",
                search_vector=[0.9, 0.1, 0.0],
                content_vector=[0.9, 0.1, 0.0],
            )
        )
        claims_case = self._bundle.case_repository.upsert(
            KnowbaseCaseDocument(
                case_id="case-claims-1",
                partition="CI",
                created_at=now,
                updated_at=now,
                title="Claims handbook",
                source_content="Claims routing guidance for reviewers.",
                summary_text="Claims summary",
                semantic_profile=CaseSemanticProfile.model_validate({"topic": ["operations"]}),
                facets=CaseFacetProfile.model_validate({"domain": ["claims"]}),
                search_text="claims handbook routing operations",
                search_vector=[0.1, 0.9, 0.0],
                content_vector=[0.1, 0.9, 0.0],
            )
        )

        listed = self._bundle.case_repository.list_by_partition("CI")
        self.assertEqual([item.case_id for item in listed], ["case-claims-1", "case-tax-1"])
        self.assertEqual(
            [item.case_id for item in self._bundle.case_repository.get_many(["case-claims-1", "missing"])],
            ["case-claims-1"],
        )

        lexical_hits = self._bundle.case_repository.search_lexical(
            KnowbaseCaseSearchQuery(
                text="tax policy",
                partition_filters=["CI"],
                facet_filters=["CI/domain/tax"],
                size=5,
            )
        )
        vector_hits = self._bundle.case_repository.search_vector(
            KnowbaseCaseSearchQuery(
                text="",
                partition_filters=["CI"],
                embedding=[1.0, 0.0, 0.0],
                size=5,
            )
        )

        self.assertEqual(tax_case.case_id, lexical_hits[0].case_id)
        self.assertEqual(claims_case.case_id, vector_hits[1].case_id)
        self.assertEqual(tax_case.case_id, vector_hits[0].case_id)
        self.assertGreater(vector_hits[0].score, vector_hits[1].score)
        self.assertEqual(lexical_hits[0].facets.get("domain"), ["tax"])

        self._bundle.case_repository.delete("case-claims-1")
        self.assertIsNone(self._bundle.case_repository.get("case-claims-1"))
        self.assertTrue((self._root / "partitions" / "CI" / "cases" / "case-tax-1.json").exists())

    def test_event_and_trace_repositories_persist_generated_ids_and_filters(self) -> None:
        now = datetime.now(timezone.utc)

        event = self._bundle.event_record_repository.save(
            EventRecord(
                event_type="case.updated",
                partition="CI",
                resource_type="case",
                resource_id="case-tax-1",
                payload=CaseEventPayload(
                    change_kind="update",
                    changed_fields=["summary_text"],
                ),
                status="pending",
                created_at=now,
            )
        )
        run = self._bundle.run_repository.save(
            AgentRun(
                partition="CI",
                agent_id="runtime-agent",
                status="completed",
                source_type="backlog",
                objective="Inspect backlog item",
                created_at=now,
            )
        )
        step = self._bundle.step_repository.save(
            RunStep(
                run_id=run.run_id,
                index=1,
                step_type="respond",
                name="Respond",
                summary="Emit final summary",
            )
        )
        artifact = self._bundle.artifact_repository.save(
            RunArtifact(
                run_id=run.run_id,
                artifact_type="response",
                title="Final response",
                content={"message": "done"},
                created_at=now,
            )
        )

        self.assertTrue(event.event_id)
        self.assertTrue(run.run_id)
        self.assertTrue(step.step_id)
        self.assertTrue(artifact.artifact_id)

        self.assertEqual(
            [item.event_id for item in self._bundle.event_record_repository.list(partition="CI", status="pending")],
            [event.event_id],
        )
        self.assertEqual(self._bundle.run_repository.get(run.run_id).status, "completed")
        self.assertEqual(
            [item.step_id for item in self._bundle.step_repository.list_for_run(run.run_id)],
            [step.step_id],
        )
        self.assertEqual(
            [item.artifact_id for item in self._bundle.artifact_repository.list_for_run(run.run_id)],
            [artifact.artifact_id],
        )

        self._bundle.step_repository.delete_for_run(run.run_id)
        self._bundle.artifact_repository.delete_for_run(run.run_id)
        self._bundle.run_repository.delete(run.run_id)
        self._bundle.event_record_repository.delete(event.event_id)

        self.assertEqual(self._bundle.step_repository.list_for_run(run.run_id), [])
        self.assertEqual(self._bundle.artifact_repository.list_for_run(run.run_id), [])
        self.assertIsNone(self._bundle.run_repository.get(run.run_id))
        self.assertIsNone(self._bundle.event_record_repository.get(event.event_id))


if __name__ == "__main__":
    unittest.main()
