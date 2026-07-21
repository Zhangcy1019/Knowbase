"""Runtime decision generator integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.runtime.llm.test_decision_generator
"""

from __future__ import annotations

import os
import unittest

from internal.models import AgentRun
from internal.runtime.contracts import (
    RuntimeAgentHints,
    RuntimeExecutionBounds,
    RuntimeMemorySnapshot,
    RuntimeProgressSnapshot,
    RuntimeRunRequest,
    RuntimeTaskContext,
    RuntimeTurnInput,
    RuntimeWorkProfile,
)
from internal.runtime.memory.state import RuntimeRunState
from internal.runtime.llm.decisioning import DefaultRuntimeDecisionGenerator
from internal.runtime.loop.planner_components import RuntimePlannerContext, RuntimePlannerStopAssessment
from internal.runtime.verification.profile import RuntimeVerificationProfile
from tests.integration.support import bootstrap_test_runtime


_TEST_RUNTIME_CONFIG = bootstrap_test_runtime()


def _has_openai_env() -> bool:
    return bool(str(os.getenv("KNOWBASE_LLM_OPENAI_API_KEY") or "").strip())


def _build_run() -> AgentRun:
    return AgentRun(
        run_id="it-runtime-decision-generator",
        partition="CI",
        agent_id="runtime.integration",
        mode="agent",
        status="running",
        source_type="manual",
        source_event_type="runtime.request",
        source_event_id="req-it-runtime-decision-generator",
        source_ref="integration-test",
        objective="Inspect the current runtime context and decide the next safe action.",
        tool_whitelist=[],
        skill_whitelist=[],
        max_steps=8,
        max_tool_calls=4,
        max_skill_calls=4,
        risk_level="medium",
    )


def _build_request() -> RuntimeRunRequest:
    return RuntimeRunRequest(
        request_id="req-it-runtime-decision-generator",
        source_type="manual",
        source_ref="integration-test",
        partition="CI",
        work=RuntimeWorkProfile(
            objective="Inspect the current runtime context and decide the next safe action.",
            mission_summary="Inspect the current runtime context and decide the next safe action.",
            instructions=[
                "Return a safe minimal decision.",
                "Prefer stopping when no real action is needed.",
                "Do not invent tool or skill ids.",
            ],
            input_context={
                "document_type": "integration_test",
                "expected_behavior": "safe_structured_decision",
            },
            capability_hints=[
                {
                    "kind": "guidance",
                    "summary": "Prefer stopping because no tools or skills are allowed.",
                }
            ],
            allowed_tools=[],
            allowed_skills=[],
            max_steps=8,
            max_tool_calls=4,
            max_skill_calls=4,
        ),
        acceptance={
            "completion_checks": [
                "return a structured decision",
                "avoid non-allowed actions",
            ]
        },
        verification=RuntimeVerificationProfile(
            enabled=False,
            mode="deterministic",
        ),
        stop_policy={"stop_when_no_executable_action": True},
        risk_policy={"risk_level": "medium"},
        risk_level="medium",
        requires_review=False,
    )


def _build_turn_input(request: RuntimeRunRequest) -> RuntimeTurnInput:
    return RuntimeTurnInput(
        run_id="it-runtime-decision-generator",
        request_id=request.request_id,
        turn_index=1,
        task=RuntimeTaskContext(
            objective=request.work.objective,
            mission_summary=request.work.mission_summary,
            instructions=list(request.work.instructions),
            partition=request.partition,
            source_type=request.source_type,
            source_ref=request.source_ref,
            work=request.work.model_copy(),
            input_context=dict(request.work.input_context),
            acceptance=request.acceptance.model_copy(),
            verification=request.verification.model_copy(),
            stop_policy=request.stop_policy.model_copy(),
            risk_policy=request.risk_policy.model_copy(),
        ),
        memory=RuntimeMemorySnapshot(
            facts={"current_phase": "integration_test"},
            observations=[],
        ),
        bounds=RuntimeExecutionBounds(
            allowed_tools=list(request.work.allowed_tools),
            allowed_skills=list(request.work.allowed_skills),
            risk_level=request.risk_level,
            requires_review=request.requires_review,
            remaining_step_budget=6,
            remaining_tool_budget=4,
            remaining_skill_budget=4,
        ),
        progress=RuntimeProgressSnapshot(
            completed_actions=[],
            recent_decisions=[],
            recent_failures=[],
            latest_response="",
        ),
        hints=RuntimeAgentHints(
            actions=list(request.work.capability_hints),
            metadata={"test_case": "runtime_decision_generator"},
        ),
    )


def _build_planner_context(request: RuntimeRunRequest, turn_input: RuntimeTurnInput) -> RuntimePlannerContext:
    return RuntimePlannerContext(
        run_id=turn_input.run_id,
        request_id=turn_input.request_id,
        turn_index=turn_input.turn_index,
        objective=turn_input.task.objective,
        mission_summary=turn_input.task.mission_summary,
        instructions=list(turn_input.task.instructions),
        partition=turn_input.task.partition,
        source_type=turn_input.task.source_type,
        source_ref=turn_input.task.source_ref,
        input_context=dict(turn_input.task.input_context),
        acceptance=turn_input.task.acceptance.model_dump(mode="json"),
        stop_policy=turn_input.task.stop_policy.model_dump(mode="json"),
        risk_policy=turn_input.task.risk_policy.model_dump(mode="json"),
        facts=dict(turn_input.memory.facts),
        observations=[],
        completed_actions=[],
        recent_decisions=[],
        recent_failures=[],
        latest_response="",
        allowed_tools=list(request.work.allowed_tools),
        allowed_skills=list(request.work.allowed_skills),
        risk_level=request.risk_level,
        requires_review=request.requires_review,
        remaining_step_budget=turn_input.bounds.remaining_step_budget,
        remaining_tool_budget=turn_input.bounds.remaining_tool_budget,
        remaining_skill_budget=turn_input.bounds.remaining_skill_budget,
        hinted_actions=list(request.work.capability_hints),
        hint_metadata={"test_case": "runtime_decision_generator"},
    )


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml to run runtime decision generator integration tests.",
)
class RuntimeDecisionGeneratorIntegrationTest(unittest.TestCase):
    """Exercise the real decision generator against the configured LLM provider."""

    def setUp(self) -> None:
        print(
            f"[runtime.llm] test={self._testMethodName} "
            f"model={_TEST_RUNTIME_CONFIG.llm.model} "
            f"base_url={os.getenv('KNOWBASE_LLM_OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def test_default_runtime_decision_generator_returns_structured_decision(self) -> None:
        run = _build_run()
        request = _build_request()
        state = RuntimeRunState()
        turn_input = _build_turn_input(request)
        planner_context = _build_planner_context(request, turn_input)
        stop_assessment = RuntimePlannerStopAssessment(
            should_stop=False,
            reason="",
            requires_review=False,
        )
        generator = DefaultRuntimeDecisionGenerator()

        decision = generator.generate(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
            planner_context=planner_context,
            stop_assessment=stop_assessment,
        )
        print(
            "[runtime.llm] decision_generator response "
            f"decision_id={decision.decision_id} should_stop={decision.should_stop} "
            f"requires_review={decision.requires_review} reasoning={decision.reasoning_summary!r} "
            f"actions={decision.model_dump(mode='json').get('actions', [])} metadata={decision.metadata}",
            flush=True,
        )

        self.assertTrue(decision.decision_id)
        self.assertEqual(decision.objective, request.work.objective)
        self.assertTrue(decision.reasoning_summary)
        self.assertIsInstance(decision.actions, list)
        self.assertIsInstance(decision.metadata, dict)

        if decision.actions:
            for action in decision.actions:
                self.assertTrue(action.summary)
                self.assertIsInstance(action.capability_id, str)
                self.assertFalse(action.capability_id, "no capabilities are allowed in this integration test")
        else:
            self.assertTrue(
                decision.should_stop,
                "empty action list should only appear when the generator decides to stop",
            )


if __name__ == "__main__":
    unittest.main()
