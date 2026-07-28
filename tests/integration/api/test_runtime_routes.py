"""Runtime route integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.api.test_runtime_routes
"""

from __future__ import annotations

import asyncio
import shutil
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
import httpx

from internal.api import KnowbaseRouteDeps
from internal.api.routes_runtime import register_runtime_routes
from internal.application.modules import build_ingest_service
from internal.application.providers import CoreProviders, IngestProviders, build_core_providers
from internal.backlog.events.queue import KnowbaseEventBacklogService
from internal.backlog.events.worker import KnowbaseEventWorker
from internal.backlog.tasks import PartitionTaskQueue
from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.knowledge.service import KnowbaseKnowledgeService
from internal.knowledge.workflow import KnowledgeDrainWorkflow
from internal.knowledge.batch import BatchWorkingSetBuilder
from internal.knowledge.governance.models import GovernanceResult
from internal.models import IngestRequest, PartitionDocument
from internal.runtime.service import KnowbaseRuntimeService
from internal.runtime.skills import SkillRuntime
from internal.runtime.tools import ToolRuntime
from internal.runtime.trace import RuntimeTraceRecorder
from tests.integration.support import load_test_runtime_config
from tests.integration.local.test_local_minimal_flow import (
    _NoopEmbeddingProvider,
    _StaticSemanticProfileExtractor,
    _StaticSummaryExtractor,
    _StaticTurnPlanner,
)


class _StubPartitionSchemaSuggester:
    def suggest(self, **kwargs):
        raise RuntimeError("partition schema suggestion is not enabled in this test")


class _StubQueryFlow:
    async def run(self, request):
        raise RuntimeError(f"query flow is not enabled in this test: {request}")


class _StaticGovernance:
    def assess_deterministic(self, *, current_schema, **kwargs):
        _ = kwargs
        return GovernanceResult(
            decision="accepted",
            accepted_schema=current_schema,
        )


class RuntimeRoutesIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._runtime_cfg = load_test_runtime_config()
        self._root = Path(self._runtime_cfg.storage.local_root).expanduser()
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)

        self._core = build_core_providers(runtime_cfg=self._runtime_cfg)
        self._core.case_write_service._embedding_provider = _NoopEmbeddingProvider()
        self._create_partition(core=self._core, partition_name="CI")
        self._ingest_service = self._build_ingest_service(core=self._core)
        self._runtime_service = self._build_runtime_service(core=self._core)
        self._backlog_service = KnowbaseEventBacklogService(repository=self._core.event_record_repository)
        self._knowledge_service = KnowbaseKnowledgeService(
            backlog_service=self._backlog_service,
            workflow=KnowledgeDrainWorkflow(
                working_set_builder=BatchWorkingSetBuilder(),
                partition_service=self._core.partition_service,
                statistics=self._core.statistics_service,
                governance=_StaticGovernance(),
                projection=self._core.projection_service,
                mutation_executor=self._core.mutation_executor,
            ),
            task_queue=PartitionTaskQueue(),
        )
        self._event_worker = KnowbaseEventWorker(
            backlog_service=self._backlog_service,
            knowledge_service=self._knowledge_service,
        )
        app = FastAPI()
        register_runtime_routes(
            app,
            deps=KnowbaseRouteDeps(
                partition_service=self._core.partition_service,
                partition_schema_suggester=_StubPartitionSchemaSuggester(),
                case_repository=self._core.case_repository,
                case_write_service=self._core.case_write_service,
                runtime_service=self._runtime_service,
                event_publisher=self._core.event_publisher,
                event_backlog_service=self._backlog_service,
                event_worker=self._event_worker,
                skill_runtime=SkillRuntime(),
                ingest_service=self._ingest_service,
                query_flow=_StubQueryFlow(),
            ),
        )
        self._app = app
    def test_drain_backlog_route_returns_run_id_and_updates_event(self) -> None:
        ingest_result = asyncio.run(
            self._ingest_service.ingest(
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
        asyncio.run(self._core.task_queue.wait_idle(partition="CI"))
        events = self._backlog_service.list_events(partition="CI")
        self.assertEqual(len(events), 1)
        event_id = events[0].event_id

        self.assertTrue(ingest_result.task_id)
        response = asyncio.run(
            self._post_json(
                path="/api/knowbase/runtime/maintenance/drain-backlog",
                payload={"partition": "CI", "limit": 20},
            )
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["action"], "drain_backlog")
        self.assertTrue(payload["ok"])
        self.assertIn("Attempted 1 backlog event", payload["summary"])
        self.assertEqual(payload["details"]["partition"], "CI")
        self.assertEqual(payload["details"]["attempted_count"], 1)
        self.assertEqual(payload["details"]["completed_count"], 0)
        self.assertEqual(payload["details"]["failed_count"], 0)
        self.assertEqual(payload["details"]["event_ids"], [event_id])
        self.assertTrue(payload["details"]["batch_id"])
        self.assertEqual(payload["details"]["run_id"], "")
        self.assertEqual(payload["details"]["run_status"], "accepted")
        self.assertFalse(payload["details"]["requires_review"])

        asyncio.run(self._core.task_queue.wait_idle(partition="CI"))

        event_record = self._backlog_service.get_event(event_id)
        self.assertIsNotNone(event_record)
        assert event_record is not None
        self.assertEqual(event_record.status, "completed")
        self.assertTrue(event_record.run_id)

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

    @staticmethod
    def _build_ingest_service(*, core: CoreProviders):
        ingest = IngestProviders(
            draft_builder=KnowbaseCaseDraftBuilder(),
            ingestor=KnowbaseCaseIngestor(),
            summary_extractor=_StaticSummaryExtractor(),
            semantic_profile_extractor=_StaticSemanticProfileExtractor(),
            facet_resolver=KnowbaseCaseFacetResolver(),
        )
        return build_ingest_service(core=core, ingest=ingest)

    @staticmethod
    def _build_runtime_service(*, core: CoreProviders) -> KnowbaseRuntimeService:
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

    async def _post_json(self, *, path: str, payload: dict[str, object]) -> httpx.Response:
        transport = httpx.ASGITransport(app=self._app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(path, json=payload)


if __name__ == "__main__":
    unittest.main()
