"""Runtime loop engine integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.runtime.loop.test_loop_engine
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone

from internal.models import AgentRun, RunArtifact, RunStep
from internal.runtime.actions.action_runner import RuntimeActionRunner
from internal.runtime.actions.capability_executor import RuntimeCapabilityExecutor
from internal.runtime.core.memory import RuntimeMemoryManager
from internal.runtime.core.policy import RuntimePolicy
from internal.runtime.core.state import RuntimeRunState
from internal.runtime.core.termination import RuntimeTerminationPolicy
from internal.runtime.loop.engine import RuntimeLoopEngine
from internal.runtime.loop.turn_planner import RuntimeTurnPlanner
from internal.runtime.trace.recorder import RuntimeTraceRecorder
from tests.integration.runtime.llm.test_decision_generator import (
    _TEST_RUNTIME_CONFIG,
    _build_request,
    _build_run,
    _has_openai_env,
)


class _InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, AgentRun] = {}

    def save(self, run: AgentRun) -> AgentRun:
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(
            update={
                "run_id": run.run_id or f"run-{int(now.timestamp() * 1000)}",
                "created_at": run.created_at or now,
                "updated_at": now,
            }
        )
        self._runs[persisted.run_id] = persisted
        return persisted

    def get(self, run_id: str) -> AgentRun | None:
        return self._runs.get(run_id)


class _InMemoryRunStepRepository:
    def __init__(self) -> None:
        self._steps: dict[str, list[RunStep]] = {}

    def save(self, step: RunStep) -> RunStep:
        now = datetime.now(timezone.utc)
        persisted = step.model_copy(
            update={
                "step_id": step.step_id or f"{step.run_id}:step:{step.index}:{int(now.timestamp() * 1000)}",
                "created_at": step.created_at or now,
            }
        )
        self._steps.setdefault(persisted.run_id, []).append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunStep]:
        return list(self._steps.get(run_id, []))


class _InMemoryRunArtifactRepository:
    def __init__(self) -> None:
        self._artifacts: dict[str, list[RunArtifact]] = {}

    def save(self, artifact: RunArtifact) -> RunArtifact:
        now = datetime.now(timezone.utc)
        persisted = artifact.model_copy(
            update={
                "artifact_id": artifact.artifact_id
                or f"{artifact.run_id}:{artifact.artifact_type}:{int(now.timestamp() * 1000)}",
                "created_at": artifact.created_at or now,
                "updated_at": now,
            }
        )
        self._artifacts.setdefault(persisted.run_id, []).append(persisted)
        return persisted

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        return list(self._artifacts.get(run_id, []))


class _NullRegistry:
    @staticmethod
    def resolve(_: str):
        return None


class _NullToolRuntime:
    registry = _NullRegistry()

    @staticmethod
    def execute(_call):
        raise AssertionError("tool execution is not expected in this loop engine integration test")


class _NullSkillRuntime:
    @staticmethod
    def execute(_invocation, context):
        raise AssertionError("skill execution is not expected in this loop engine integration test")

    @staticmethod
    def resolve_spec(_skill_id: str):
        return None


def _build_loop_test_runtime() -> tuple[RuntimeLoopEngine, _InMemoryRunRepository, _InMemoryRunStepRepository, _InMemoryRunArtifactRepository]:
    run_repository = _InMemoryRunRepository()
    step_repository = _InMemoryRunStepRepository()
    artifact_repository = _InMemoryRunArtifactRepository()
    trace_recorder = RuntimeTraceRecorder(
        run_repository=run_repository,
        step_repository=step_repository,
        artifact_repository=artifact_repository,
    )
    capability_executor = RuntimeCapabilityExecutor(
        run_repository=run_repository,
        tool_runtime=_NullToolRuntime(),
        skill_runtime=_NullSkillRuntime(),
        trace_recorder=trace_recorder,
    )
    memory_manager = RuntimeMemoryManager()
    action_runner = RuntimeActionRunner(
        capability_executor=capability_executor,
        policy=RuntimePolicy(capability_executor=capability_executor),
        memory_manager=memory_manager,
        trace_recorder=trace_recorder,
    )
    engine = RuntimeLoopEngine(
        capability_executor=capability_executor,
        planner=RuntimeTurnPlanner(),
        action_runner=action_runner,
        memory_manager=memory_manager,
        termination_policy=RuntimeTerminationPolicy(),
        trace_recorder=trace_recorder,
    )
    return engine, run_repository, step_repository, artifact_repository


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml to run runtime loop engine integration tests.",
)
class RuntimeLoopEngineIntegrationTest(unittest.TestCase):
    """Exercise the real loop engine pipeline against the configured LLM provider."""

    def setUp(self) -> None:
        print(
            f"[runtime.loop] test={self._testMethodName} "
            f"model={_TEST_RUNTIME_CONFIG.llm.model} "
            f"base_url={os.getenv('KNOWBASE_LLM_OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def test_runtime_loop_engine_stops_cleanly_without_actions(self) -> None:
        engine, run_repository, step_repository, artifact_repository = _build_loop_test_runtime()
        run = run_repository.save(_build_run())
        request = _build_request().model_copy(
            update={
                "prompt": (
                    "This is a runtime loop engine integration test. "
                    "Return should_stop=true with no actions. "
                    "Use a short reasoning summary and do not propose tool or skill calls."
                ),
            }
        )
        state = RuntimeRunState()

        state, final_status, requires_review = engine.run(
            run=run,
            request=request,
            state=state,
        )
        print(
            "[runtime.loop] loop_engine stop response "
            f"final_status={final_status} turn_count={state.turn_count} "
            f"decisions={[item.model_dump(mode='json') for item in state.decision_history]} "
            f"steps={[item.step_type for item in step_repository.list_for_run(run.run_id)]} "
            f"artifacts={[item.artifact_type for item in artifact_repository.list_for_run(run.run_id)]}",
            flush=True,
        )

        self.assertEqual(final_status, "completed")
        self.assertFalse(requires_review)
        self.assertEqual(state.turn_count, 1)
        self.assertEqual(len(state.decision_history), 1)
        self.assertTrue(state.decision_history[0].should_stop)
        self.assertEqual(state.applied_actions, [])
        self.assertGreaterEqual(len(step_repository.list_for_run(run.run_id)), 1)

    def test_runtime_loop_engine_records_summary_then_stops(self) -> None:
        engine, run_repository, step_repository, artifact_repository = _build_loop_test_runtime()
        run = run_repository.save(_build_run())
        request = _build_request().model_copy(
            update={
                "prompt": (
                    "This is a runtime loop engine integration test. "
                    "Return should_stop=true with no actions. "
                    "Provide a short action_plan_summary and do not propose tool_call or skill_call actions."
                ),
            }
        )
        state = RuntimeRunState()

        state, final_status, requires_review = engine.run(
            run=run,
            request=request,
            state=state,
        )
        print(
            "[runtime.loop] loop_engine summary response "
            f"final_status={final_status} turn_count={state.turn_count} "
            f"responses={state.response_messages} applied_actions={state.applied_actions} "
            f"decisions={[item.model_dump(mode='json') for item in state.decision_history]} "
            f"steps={[item.step_type for item in step_repository.list_for_run(run.run_id)]} "
            f"artifacts={[item.artifact_type for item in artifact_repository.list_for_run(run.run_id)]}",
            flush=True,
        )

        self.assertEqual(final_status, "completed")
        self.assertFalse(requires_review)
        self.assertEqual(state.turn_count, 1)
        self.assertEqual(len(state.decision_history), 1)
        self.assertTrue(state.decision_history[0].should_stop)
        self.assertTrue(state.response_messages)
        self.assertEqual(state.applied_actions, [])
        self.assertIn("response", [item.get("kind") for item in state.observations])
        self.assertGreaterEqual(len(step_repository.list_for_run(run.run_id)), 1)


if __name__ == "__main__":
    unittest.main()
