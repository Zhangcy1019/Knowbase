"""Runtime service integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.runtime.test_runtime_service
"""

from __future__ import annotations

import asyncio
import os
import unittest

from internal.runtime.loop.turn_planner import RuntimeTurnPlanner
from internal.runtime.service import KnowbaseRuntimeService
from tests.integration.runtime.llm.test_decision_generator import (
    _TEST_RUNTIME_CONFIG,
    _build_request,
    _has_openai_env,
)
from tests.integration.runtime.loop.test_loop_engine import (
    _InMemoryRunArtifactRepository,
    _InMemoryRunRepository,
    _InMemoryRunStepRepository,
    _NullSkillRuntime,
    _NullToolRuntime,
)


class _StaticPartitionService:
    @staticmethod
    def get_partition(partition: str):
        return {"partition": partition, "status": "active"} if partition.strip() else None


class _InactivePartitionService:
    @staticmethod
    def get_partition(partition: str):
        return {"partition": partition, "status": "disabled"} if partition.strip() else None


class RuntimeServicePartitionValidationTest(unittest.TestCase):
    def _build_service(self, *, partition_service) -> KnowbaseRuntimeService:
        run_repository = _InMemoryRunRepository()
        step_repository = _InMemoryRunStepRepository()
        artifact_repository = _InMemoryRunArtifactRepository()

        from internal.runtime.trace.recorder import RuntimeTraceRecorder

        trace_recorder = RuntimeTraceRecorder(
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
        )
        return KnowbaseRuntimeService(
            partition_service=partition_service,
            case_repository=None,
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
            tool_runtime=_NullToolRuntime(),
            skill_runtime=_NullSkillRuntime(),
            planner=RuntimeTurnPlanner(),
            trace_recorder=trace_recorder,
        )

    def test_runtime_service_rejects_empty_partition(self) -> None:
        service = self._build_service(partition_service=_StaticPartitionService())
        request = _build_request().model_copy(update={"partition": ""})

        with self.assertRaisesRegex(ValueError, "runtime request partition must not be empty"):
            asyncio.run(service.run_request(request=request))

    def test_runtime_service_rejects_inactive_partition(self) -> None:
        service = self._build_service(partition_service=_InactivePartitionService())
        request = _build_request()

        with self.assertRaisesRegex(ValueError, "partition is not active: CI"):
            asyncio.run(service.run_request(request=request))


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml to run runtime service integration tests.",
)
class RuntimeServiceIntegrationTest(unittest.TestCase):
    """Exercise the runtime service end-to-end with real planner/model and in-memory persistence."""

    def setUp(self) -> None:
        print(
            f"[runtime.service] test={self._testMethodName} "
            f"model={_TEST_RUNTIME_CONFIG.llm.model} "
            f"base_url={os.getenv('KNOWBASE_LLM_OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def _build_service(self) -> KnowbaseRuntimeService:
        run_repository = _InMemoryRunRepository()
        step_repository = _InMemoryRunStepRepository()
        artifact_repository = _InMemoryRunArtifactRepository()

        from internal.runtime.trace.recorder import RuntimeTraceRecorder

        trace_recorder = RuntimeTraceRecorder(
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
        )
        return KnowbaseRuntimeService(
            partition_service=_StaticPartitionService(),
            case_repository=None,
            run_repository=run_repository,
            step_repository=step_repository,
            artifact_repository=artifact_repository,
            tool_runtime=_NullToolRuntime(),
            skill_runtime=_NullSkillRuntime(),
            planner=RuntimeTurnPlanner(),
            trace_recorder=trace_recorder,
        )

    def test_runtime_service_run_request_stops_cleanly(self) -> None:
        service = self._build_service()
        request = _build_request().model_copy(
            update={
                "prompt": (
                    "This is a runtime service integration test. "
                    "Return should_stop=true with no actions. "
                    "Use a short reasoning summary and stop immediately."
                ),
            }
        )

        result = asyncio.run(service.run_request(request=request))
        print(
            "[runtime.service] stop result "
            f"run_id={result.run_id} status={result.status} "
            f"final_summary={result.final_summary!r} reasoning_summary={result.reasoning_summary!r} "
            f"applied_actions={result.applied_actions} "
            f"steps={[item.step_type for item in result.steps]} "
            f"artifacts={[item.artifact_type for item in result.artifacts]}",
            flush=True,
        )

        self.assertEqual(result.request_id, request.request_id)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.run_id)
        self.assertTrue(result.reasoning_summary)
        self.assertEqual(result.applied_actions, [])
        self.assertGreaterEqual(len(result.steps), 1)
        self.assertGreaterEqual(len(result.artifacts), 1)
        self.assertIn("runtime_request", [item.artifact_type for item in result.artifacts])

    def test_runtime_service_run_request_executes_respond_action(self) -> None:
        service = self._build_service()
        request = _build_request().model_copy(
            update={
                "prompt": (
                    "This is a runtime service integration test. "
                    "Return exactly one respond action with a short response, "
                    "and set should_stop=true. Do not propose tool or skill actions."
                ),
            }
        )

        result = asyncio.run(service.run_request(request=request))
        print(
            "[runtime.service] respond result "
            f"run_id={result.run_id} status={result.status} "
            f"final_summary={result.final_summary!r} reasoning_summary={result.reasoning_summary!r} "
            f"applied_actions={result.applied_actions} "
            f"steps={[item.step_type for item in result.steps]} "
            f"artifacts={[item.artifact_type for item in result.artifacts]}",
            flush=True,
        )

        self.assertEqual(result.request_id, request.request_id)
        self.assertEqual(result.status, "completed")
        self.assertTrue(result.run_id)
        self.assertTrue(result.final_summary)
        self.assertTrue(result.reasoning_summary)
        self.assertTrue(result.applied_actions)
        self.assertGreaterEqual(len(result.steps), 2)
        self.assertGreaterEqual(len(result.artifacts), 2)
        self.assertIn("runtime_request", [item.artifact_type for item in result.artifacts])
        self.assertIn("decision", [item.artifact_type for item in result.artifacts])


if __name__ == "__main__":
    unittest.main()
