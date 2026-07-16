"""Runtime OpenAI provider integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.runtime.providers.test_openai_providers
"""

from __future__ import annotations

import os
import unittest

from internal.runtime.llm.prompt_builder import RuntimeDecisionPrompt
from internal.runtime.providers.openai_client import DefaultOpenAIClient, OpenAIChatRequest
from internal.runtime.providers.openai_runtime_adapter import DefaultRuntimeModelAdapter
from tests.integration.support import bootstrap_test_runtime


_TEST_RUNTIME_CONFIG = bootstrap_test_runtime()


def _has_openai_env() -> bool:
    return bool(str(os.getenv("OPENAI_API_KEY") or "").strip())


def _resolve_test_model() -> str:
    return _TEST_RUNTIME_CONFIG.llm.model.strip() or "gpt-4o-mini"


@unittest.skipUnless(
    _has_openai_env(),
    "Set llm.openai.api_key in config/app.test.yaml or OPENAI_API_KEY to run runtime OpenAI integration tests.",
)
class RuntimeOpenAIProvidersIntegrationTest(unittest.TestCase):
    """Exercise real OpenAI-backed runtime provider calls."""

    def setUp(self) -> None:
        print(
            f"[runtime.providers] test={self._testMethodName} "
            f"model={_resolve_test_model()} "
            f"base_url={os.getenv('OPENAI_BASE_URL', '') or '<default>'}",
            flush=True,
        )

    def test_default_openai_client_create_chat_returns_json_object(self) -> None:
        client = DefaultOpenAIClient.from_env()

        response = client.create_chat(
            request=OpenAIChatRequest(
                model=_resolve_test_model(),
                system_prompt="You are a precise test assistant. Return JSON only.",
                user_prompt=(
                    'Return a JSON object with keys "message" and "ok". '
                    'Set "message" to "runtime provider integration" and "ok" to true.'
                ),
                response_format="json_object",
                temperature=0.0,
                max_output_tokens=200,
                metadata={"test_case": "runtime_openai_client_integration"},
            )
        )
        print(
            "[runtime.providers] openai_client response "
            f"model={response.model} finish_reason={response.finish_reason} "
            f"content_text={response.content_text!r} content_json={response.content_json}",
            flush=True,
        )

        self.assertEqual(response.content_json.get("message"), "runtime provider integration")
        self.assertIs(response.content_json.get("ok"), True)
        self.assertTrue(response.model)
        self.assertIsInstance(response.usage, dict)
        self.assertGreaterEqual(response.usage.get("total_tokens", 0), 0)

    def test_default_runtime_model_adapter_invoke_returns_structured_payload(self) -> None:
        adapter = DefaultRuntimeModelAdapter.from_env()

        response = adapter.invoke(
            prompt=RuntimeDecisionPrompt(
                model=_resolve_test_model(),
                system=(
                    "You are a runtime planning agent test double. "
                    "Return exactly one JSON object that matches the provided schema."
                ),
                instruction=(
                    "Produce a no-op runtime decision for integration testing.\n"
                    'Use reasoning_summary="integration test".\n'
                    'Use action_plan_summary="stop immediately".\n'
                    "Set should_stop=true.\n"
                    'Set stop_reason="completed".\n'
                    "Set requires_review=false.\n"
                    'Set review_reason="unknown".\n'
                    "Set notes to an empty array.\n"
                    "Set metadata to an object with {\"test\": true}.\n"
                    "Set actions to an empty array.\n"
                    "Return JSON only."
                ),
                response_schema={
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "reasoning_summary",
                        "action_plan_summary",
                        "should_stop",
                        "stop_reason",
                        "requires_review",
                        "review_reason",
                        "notes",
                        "metadata",
                        "actions",
                    ],
                    "properties": {
                        "reasoning_summary": {"type": "string"},
                        "action_plan_summary": {"type": "string"},
                        "should_stop": {"type": "boolean"},
                        "stop_reason": {"type": "string"},
                        "requires_review": {"type": "boolean"},
                        "review_reason": {"type": "string"},
                        "notes": {"type": "array", "items": {"type": "string"}},
                        "metadata": {"type": "object"},
                        "actions": {"type": "array", "items": {"type": "object"}},
                    },
                },
                temperature=0.0,
                max_output_tokens=300,
                context={"test_case": "runtime_model_adapter_integration"},
            )
        )
        print(
            "[runtime.providers] runtime_model_adapter response "
            f"model={response.model_name} finish_reason={response.finish_reason} "
            f"raw_text={response.raw_text!r} payload={response.payload}",
            flush=True,
        )

        self.assertEqual(response.payload.get("reasoning_summary"), "integration test")
        self.assertEqual(response.payload.get("action_plan_summary"), "stop immediately")
        self.assertIs(response.payload.get("should_stop"), True)
        self.assertEqual(response.payload.get("stop_reason"), "completed")
        self.assertIs(response.payload.get("requires_review"), False)
        self.assertEqual(response.payload.get("review_reason"), "unknown")
        self.assertEqual(response.payload.get("notes"), [])
        self.assertEqual(response.payload.get("metadata"), {"test": True})
        self.assertEqual(response.payload.get("actions"), [])
        self.assertTrue(response.model_name)
        self.assertIsInstance(response.usage, dict)


if __name__ == "__main__":
    unittest.main()
