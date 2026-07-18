"""Service entrypoint for embedding provider construction."""

from __future__ import annotations

from functools import lru_cache

from internal.infrastructure.ai.embedding import EmbeddingConfig, OpenAICompatibleEmbeddingProvider
from internal.infrastructure.ai.embedding_contracts import EmbeddingProvider


@lru_cache(maxsize=1)
def create_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    if config.provider != "openai_compatible":
        raise RuntimeError(f"Unsupported knowledge embedding provider: {config.provider}")
    return OpenAICompatibleEmbeddingProvider(config)


__all__ = ["create_embedding_provider"]
