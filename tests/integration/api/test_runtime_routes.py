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
from unittest.mock import patch

from fastapi import FastAPI
import httpx

from internal.api import KnowbaseRouteDeps
from internal.api.routes_runtime import register_runtime_routes
from internal.application.modules import build_ingest_service
from internal.application.providers import CoreProviders, IngestProviders, build_core_providers
from internal.backlog.queue import KnowbaseEventBacklogService
from internal.backlog.worker import KnowbaseEventWorker
from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.knowledge.dispatch import (
    KnowbaseKnowledgeDispatchService,
    KnowledgeTaskBuilder,
    RuntimeRequestBuilder,
)
from internal.knowledge.planning import BacklogPreparationPlanner, BatchWorkingSetBuilder
from internal.models import IngestRequest, PartitionDocument
from internal.runtime.service import KnowbaseRuntimeService
from internal.runtime.skills import SkillRuntime
from internal.runtime.tools import ToolRuntime
from internal.runtime.trace import RuntimeTraceRecorder
from tests.integration.support import load_test_runtime_config
from tests.integration.text.test_text_minimal_flow import (
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


class RuntimeRoutesIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._runtime_cfg = load_test_runtime_config()
        self._root = Path(self._runtime_cfg.storage.text_root).expanduser()
        shutil.rmtree(self._root, ignore_errors=True)
        self._root.mkdir(parents=True, exist_ok=True)

        self._core = build_core_providers(runtime_cfg=self._runtime_cfg)
        self._create_partition(core=self._core, partition_name="CI")
        self._ingest_service = self._build_ingest_service(core=self._core)
        self._runtime_service = self._build_runtime_service(core=self._core)
        self._backlog_service = KnowbaseEventBacklogService(repository=self._core.event_record_repository)
        self._dispatch_service = KnowbaseKnowledgeDispatchService(
            task_builder=KnowledgeTaskBuilder(
                working_set_builder=BatchWorkingSetBuilder(),
                preparation_planner=BacklogPreparationPlanner(
                    partition_service=self._core.partition_service,
                    case_repository=self._core.case_repository,
                ),
            ),
            runtime_request_builder=RuntimeRequestBuilder(),
        )
        self._event_worker = KnowbaseEventWorker(
            backlog_service=self._backlog_service,
            dispatch_service=self._dispatch_service,
            runtime_service=self._runtime_service,
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
        with patch("internal.domain.case.write_service.create_embedding_provider", return_value=_NoopEmbeddingProvider()):
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

        self.assertTrue(ingest_result.backlog_event_id)
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
        self.assertEqual(payload["details"]["completed_count"], 1)
        self.assertEqual(payload["details"]["failed_count"], 0)
        self.assertEqual(payload["details"]["event_ids"], [ingest_result.backlog_event_id])
        self.assertTrue(payload["details"]["batch_id"])
        self.assertTrue(payload["details"]["run_id"])
        self.assertEqual(payload["details"]["run_status"], "completed")
        self.assertFalse(payload["details"]["requires_review"])

        event_record = self._backlog_service.get_event(ingest_result.backlog_event_id)
        self.assertIsNotNone(event_record)
        assert event_record is not None
        self.assertEqual(event_record.status, "completed")
        self.assertEqual(event_record.run_id, payload["details"]["run_id"])

        run = self._runtime_service.get_run(payload["details"]["run_id"])
        self.assertIsNotNone(run)
        assert run is not None
        self.assertEqual(run.partition, "CI")
        self.assertEqual(run.status, "completed")

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
            facet_schema={},
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
