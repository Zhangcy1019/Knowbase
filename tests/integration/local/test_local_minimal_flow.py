"""Local-backend minimal flow integration test.

Run:
    cd knowbase
    python3 -m unittest tests.integration.local.test_local_minimal_flow
"""

from __future__ import annotations

import asyncio
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from internal.application.modules import (
    build_ingest_service,
)
from internal.application.providers import CoreProviders, IngestProviders, build_core_providers
from internal.backlog.queue import KnowbaseEventBacklogService
from internal.backlog.worker import KnowbaseEventWorker
from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.knowledge.integrations import RuntimeRequestFactory
from internal.knowledge.service import KnowbaseKnowledgeService
from internal.knowledge.workflow import KnowledgeDrainWorkflow
from internal.knowledge.batch import BatchContextBuilder, BatchWorkingSetBuilder
from internal.models import IngestRequest, PartitionDocument, PartitionFacetSchema
from internal.models.semantic_profile import CaseSemanticProfile
from internal.runtime.contracts import RuntimeDecision
from internal.runtime.loop.turn_planner import RuntimeTurnPlannerPort
from internal.runtime.service import KnowbaseRuntimeService
from internal.runtime.skills import SkillRuntime
from internal.runtime.tools import ToolRuntime
from internal.runtime.trace import RuntimeTraceRecorder
from tests.integration.support import load_test_runtime_config


class _StaticSummaryExtractor:
    async def extract(self, *, title: str, source_content: str) -> str:
        return f"{title}: {source_content[:32]}".strip()


class _StaticSemanticProfileExtractor:
    async def extract(
        self,
        *,
        title: str,
        source_content: str,
        facet_definitions=None,
        semantic_index=None,
    ) -> CaseSemanticProfile:
        _ = title, facet_definitions, semantic_index
        payload = {
            "topic": ["policy"],
            "source_kind": ["document"],
        }
        if "tax" in source_content.lower():
            payload["domain"] = ["tax"]
        return CaseSemanticProfile.model_validate(payload)


class _NoopEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0, 0.0, 0.0] for _ in texts]


class _StaticTurnPlanner(RuntimeTurnPlannerPort):
    def plan_turn(self, *, run, request, state, turn_input) -> RuntimeDecision:
        _ = run, request, state
        return RuntimeDecision(
            decision_id=f"turn:{turn_input.turn_index}",
            objective=turn_input.task.objective,
            reasoning_summary="Backlog batch inspected and summarized.",
            should_stop=True,
            metadata={
                "turn_index": turn_input.turn_index,
                "action_plan_summary": "Batch summarized for operator review.",
            },
        )


class LocalMinimalFlowIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._runtime_cfg = load_test_runtime_config()
        self._root = Path(self._runtime_cfg.storage.local_root).expanduser()
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        pass

    def test_local_backend_minimal_flow_runs_end_to_end(self) -> None:
        core = build_core_providers(runtime_cfg=self._runtime_cfg)
        self._create_partition(core=core, partition_name="CI")

        ingest_service = self._build_ingest_service(core=core)
        runtime_service = self._build_runtime_service(core=core)
        backlog_service = KnowbaseEventBacklogService(repository=core.event_record_repository)
        knowledge_service = KnowbaseKnowledgeService(
            backlog_service=backlog_service,
            workflow=KnowledgeDrainWorkflow(
                request_factory=RuntimeRequestFactory(
                working_set_builder=BatchWorkingSetBuilder(),
                context_builder=BatchContextBuilder(
                    partition_service=core.partition_service,
                    case_repository=core.case_repository,
                ),
                ),
                runtime_service=runtime_service,
            ),
        )
        worker = KnowbaseEventWorker(
            backlog_service=backlog_service,
            knowledge_service=knowledge_service,
        )

        with patch("internal.domain.case.write_service.create_embedding_provider", return_value=_NoopEmbeddingProvider()):
            ingest_result = asyncio.run(
                ingest_service.ingest(
                    IngestRequest(
                        partition_name="CI",
                        title="Tax policy note",
                        source_content="This tax document should enter the backlog and be summarized by runtime.",
                        source_refs=["doc://tax-note-1"],
                        author="integration-test",
                        source="user",
                    )
                )
            )

        self.assertTrue(ingest_result.case_id)
        self.assertEqual(ingest_result.partition, "CI")
        self.assertTrue(ingest_result.backlog_event_id)

        events_before = backlog_service.list_events(partition="CI")
        self.assertEqual(len(events_before), 1)
        self.assertEqual(events_before[0].status, "pending")

        worker_result = asyncio.run(worker.run_once(partition="CI", trigger_source="integration_test"))
        self.assertEqual(worker_result.attempted_count, 1)
        self.assertEqual(worker_result.completed_count, 1)
        self.assertEqual(worker_result.failed_count, 0)
        self.assertTrue(worker_result.accepted)
        event_after = backlog_service.get_event(ingest_result.backlog_event_id)
        assert event_after is not None
        runtime_result = runtime_service.get_run(event_after.run_id)
        assert runtime_result is not None
        self.assertEqual(runtime_result.status, "completed")
        self.assertTrue(runtime_result.run_id)
        self.assertEqual(runtime_result.applied_actions, [])
        self.assertGreaterEqual(len(runtime_result.steps), 1)
        self.assertGreaterEqual(len(runtime_result.artifacts), 1)

        events_after = backlog_service.list_events(partition="CI")
        self.assertEqual(len(events_after), 1)
        self.assertEqual(events_after[0].status, "completed")
        self.assertEqual(events_after[0].run_id, runtime_result.run_id)

        replay = runtime_service.get_trace_replay(runtime_result.run_id)
        self.assertIsNotNone(replay)
        assert replay is not None
        self.assertEqual(replay.run.run_id, runtime_result.run_id)
        self.assertGreaterEqual(len(replay.turns), 1)

        cases_dir = self._root / "cases"
        events_dir = self._root / "events"
        runs_dir = self._root / "runs"
        steps_dir = self._root / "run_steps"
        artifacts_dir = self._root / "run_artifacts"
        self.assertEqual(len(list(cases_dir.glob("*.json"))), 1)
        self.assertEqual(len(list(events_dir.glob("*.json"))), 1)
        self.assertEqual(len(list(runs_dir.glob("*.json"))), 1)
        self.assertGreaterEqual(len(list(steps_dir.glob("*.json"))), 2)
        self.assertGreaterEqual(len(list(artifacts_dir.glob("*.json"))), 2)

    def _build_ingest_service(self, *, core: CoreProviders):
        ingest = IngestProviders(
            draft_builder=KnowbaseCaseDraftBuilder(),
            ingestor=KnowbaseCaseIngestor(),
            summary_extractor=_StaticSummaryExtractor(),
            semantic_profile_extractor=_StaticSemanticProfileExtractor(),
            facet_resolver=KnowbaseCaseFacetResolver(),
        )
        return build_ingest_service(core=core, ingest=ingest)

    def _build_runtime_service(self, *, core: CoreProviders) -> KnowbaseRuntimeService:
        trace_recorder = RuntimeTraceRecorder(
            run_repository=core.run_repository,
            step_repository=core.step_repository,
            artifact_repository=core.artifact_repository,
        )
        return KnowbaseRuntimeService(
            partition_service=core.partition_service,
            case_repository=core.case_repository,
            run_repository=core.run_repository,
            step_repository=core.step_repository,
            artifact_repository=core.artifact_repository,
            tool_runtime=ToolRuntime(),
            skill_runtime=SkillRuntime(),
            planner=_StaticTurnPlanner(),
            trace_recorder=trace_recorder,
        )

    @staticmethod
    def _create_partition(*, core: CoreProviders, partition_name: str) -> None:
        now = datetime.now(timezone.utc)
        core.partition_service.save_partition(
            PartitionDocument(
                partition_name=partition_name,
                scenario_description="Integration test partition",
                status="active",
                created_at=now,
                updated_at=now,
            )
        )
        core.partition_service.save_facet_schema(
            partition_name=partition_name,
            facet_schema=PartitionFacetSchema(),
        )


if __name__ == "__main__":
    unittest.main()
