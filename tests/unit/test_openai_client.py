"""Tests for provider-specific OpenAI-compatible request options.

Run with:
    python3 -m unittest tests.unit.test_openai_client
"""

import unittest
from types import SimpleNamespace

from internal.infrastructure.ai.openai_client import DefaultOpenAIClient, OpenAIChatRequest


class _Completions:
    def __init__(self):
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace()


class _Client:
    def __init__(self, completions):
        self.chat = SimpleNamespace(completions=completions)


class OpenAIClientTest(unittest.TestCase):
    def test_minimax_m3_disables_thinking(self):
        completions = _Completions()
        client = DefaultOpenAIClient.__new__(DefaultOpenAIClient)
        client._client = _Client(completions)

        client._create_completion(
            request=OpenAIChatRequest(model="MiniMax-M3"),
            include_response_format=True,
        )

        self.assertEqual(
            completions.kwargs["extra_body"],
            {"thinking": {"type": "disabled"}},
        )

    def test_other_models_do_not_receive_minimax_options(self):
        completions = _Completions()
        client = DefaultOpenAIClient.__new__(DefaultOpenAIClient)
        client._client = _Client(completions)

        client._create_completion(
            request=OpenAIChatRequest(model="gpt-4o-mini"),
            include_response_format=True,
        )

        self.assertNotIn("extra_body", completions.kwargs)


if __name__ == "__main__":
    unittest.main()
