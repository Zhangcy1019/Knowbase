"""Runtime turn planner integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.runtime.loop.test_turn_planner
"""

from __future__ import annotations

import os
import unittest

from internal.runtime.core.state import RuntimeRunState
from internal.runtime.loop.turn_planner import RuntimeTurnPlanner
from tests.integration.runtime.llm.test_decision_generator import (
    _TEST_RUNTIME_CONFIG,
    _build_request,
    _build_run,
    _build_turn_input,
    _has_openai_env,
)


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml to run runtime turn planner integration tests.",
)
class RuntimeTurnPlannerIntegrationTest(unittest.TestCase):
    """Exercise the real turn planner pipeline against the configured LLM provider."""

    def setUp(self) -> None:
        print(
            f"[runtime.loop] test={self._testMethodName} "
            f"model={_TEST_RUNTIME_CONFIG.llm.model} "
            f"base_url={os.getenv('KNOWBASE_LLM_OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def test_runtime_turn_planner_returns_structured_decision(self) -> None:
        run = _build_run()
        request = _build_request()
        state = RuntimeRunState()
        turn_input = _build_turn_input(request)
        planner = RuntimeTurnPlanner()

        decision = planner.plan_turn(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
        )
        print(
            "[runtime.loop] turn_planner response "
            f"decision_id={decision.decision_id} should_stop={decision.should_stop} "
            f"requires_review={decision.requires_review} reasoning={decision.reasoning_summary!r} "
            f"actions={decision.model_dump(mode='json').get('actions', [])} metadata={decision.metadata}",
            flush=True,
        )

        self.assertTrue(decision.decision_id)
        self.assertEqual(decision.objective, request.objective)
        self.assertTrue(decision.reasoning_summary)
        self.assertIsInstance(decision.actions, list)
        self.assertIsInstance(decision.metadata, dict)
        self.assertEqual(decision.metadata.get("turn_index"), turn_input.turn_index)

        if decision.actions:
            for action in decision.actions:
                self.assertTrue(action.summary)
                self.assertIn(action.kind, {"respond", "stop", "tool_call", "skill_call"})
        else:
            self.assertTrue(
                decision.should_stop,
                "empty action list should only appear when the planner decides to stop",
            )

    def test_runtime_turn_planner_stop_evaluator_short_circuits_when_budget_exhausted(self) -> None:
        run = _build_run()
        request = _build_request()
        state = RuntimeRunState()
        turn_input = _build_turn_input(request).model_copy(
            update={
                "turn_index": 2,
                "bounds": _build_turn_input(request).bounds.model_copy(
                    update={
                        "remaining_step_budget": 0,
                        "remaining_tool_budget": 0,
                        "remaining_skill_budget": 0,
                    }
                ),
            }
        )
        planner = RuntimeTurnPlanner()

        decision = planner.plan_turn(
            run=run,
            request=request,
            state=state,
            turn_input=turn_input,
        )
        print(
            "[runtime.loop] turn_planner stop response "
            f"decision_id={decision.decision_id} should_stop={decision.should_stop} "
            f"requires_review={decision.requires_review} reasoning={decision.reasoning_summary!r} "
            f"actions={decision.model_dump(mode='json').get('actions', [])} metadata={decision.metadata}",
            flush=True,
        )

        self.assertTrue(decision.should_stop)
        self.assertEqual(decision.metadata.get("stop_reason"), "budget_exhausted")
        self.assertEqual(decision.metadata.get("turn_index"), 2)
        self.assertEqual(decision.actions, [])


if __name__ == "__main__":
    unittest.main()
