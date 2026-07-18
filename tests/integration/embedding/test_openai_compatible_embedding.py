"""Embedding provider integration tests.

Run:
    cd knowbase
    python3 -m unittest tests.integration.embedding.test_openai_compatible_embedding
"""

from __future__ import annotations

import os
import unittest

from internal.infrastructure.ai import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
    create_embedding_provider,
)
from tests.integration.support import bootstrap_test_runtime


_TEST_RUNTIME_CONFIG = bootstrap_test_runtime()


def _has_embedding_env() -> bool:
    endpoint = str(os.getenv("KNOWBASE_EMBEDDING_ENDPOINT") or "").strip()
    base_url = str(os.getenv("KNOWBASE_EMBEDDING_BASE_URL") or "").strip()
    return bool(endpoint or base_url)


@unittest.skipUnless(
    _has_embedding_env(),
    "Set embedding.endpoint or embedding.base_url in config/app.test.yaml to run embedding integration tests.",
)
class OpenAICompatibleEmbeddingIntegrationTest(unittest.TestCase):
    """Exercise the real embedding provider against the configured endpoint."""

    def setUp(self) -> None:
        create_embedding_provider.cache_clear()
        self._config = EmbeddingConfig(
            provider=_TEST_RUNTIME_CONFIG.embedding.provider,
            model_name=_TEST_RUNTIME_CONFIG.embedding.model_name,
            endpoint=_TEST_RUNTIME_CONFIG.embedding.endpoint,
            base_url=_TEST_RUNTIME_CONFIG.embedding.base_url,
            api_key=_TEST_RUNTIME_CONFIG.embedding.api_key,
            dimensions=_TEST_RUNTIME_CONFIG.embedding.dimensions,
            query_prefix=_TEST_RUNTIME_CONFIG.embedding.query_prefix,
            document_prefix=_TEST_RUNTIME_CONFIG.embedding.document_prefix,
            timeout_seconds=_TEST_RUNTIME_CONFIG.embedding.timeout_seconds,
        )
        print(
            f"[embedding] test={self._testMethodName} "
            f"provider={self._config.provider} "
            f"model={self._config.model_name or '<default>'} "
            f"endpoint={self._config.endpoint or self._config.base_url}",
            flush=True,
        )

    def _call_or_skip(self, func):
        try:
            return func()
        except RuntimeError as exc:
            message = str(exc)
            if (
                "NameResolutionError" in message
                or "Max retries exceeded" in message
                or "Embedding request failed" in message
                or "SSLEOFError" in message
                or "UNEXPECTED_EOF_WHILE_READING" in message
            ):
                self.skipTest(f"embedding endpoint unavailable in current environment: {message}")
            raise

    def test_create_embedding_provider_embed_query_returns_expected_dimensions(self) -> None:
        provider = create_embedding_provider(self._config)

        vector = self._call_or_skip(lambda: provider.embed_query("tax policy integration test query"))
        print(
            "[embedding] query vector "
            f"dimensions={len(vector)} sample={vector[:5]}",
            flush=True,
        )

        self.assertIsInstance(vector, list)
        self.assertGreater(len(vector), 0)
        if self._config.dimensions > 0:
            self.assertEqual(len(vector), self._config.dimensions)

    def test_openai_compatible_embedding_provider_embed_documents_returns_batch_vectors(self) -> None:
        provider = OpenAICompatibleEmbeddingProvider(self._config)
        documents = [
            "Tax policy summary for integration testing.",
            "Claims workflow note for embedding batch validation.",
        ]

        vectors = self._call_or_skip(lambda: provider.embed_documents(documents))
        print(
            "[embedding] document vectors "
            f"count={len(vectors)} dims={[len(item) for item in vectors]} "
            f"first_sample={vectors[0][:5] if vectors else []}",
            flush=True,
        )

        self.assertEqual(len(vectors), len(documents))
        for vector in vectors:
            self.assertIsInstance(vector, list)
            self.assertGreater(len(vector), 0)
            if self._config.dimensions > 0:
                self.assertEqual(len(vector), self._config.dimensions)


if __name__ == "__main__":
    unittest.main()
