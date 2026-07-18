"""Service entrypoint for embedding provider construction."""

from __future__ import annotations

from functools import lru_cache

from internal.embedding.contracts import EmbeddingProvider
from internal.embedding.provider import EmbeddingConfig, OpenAICompatibleEmbeddingProvider


@lru_cache(maxsize=1)
def create_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    if config.provider != "openai_compatible":
        raise RuntimeError(f"Unsupported knowledge embedding provider: {config.provider}")
    return OpenAICompatibleEmbeddingProvider(config)


__all__ = ["create_embedding_provider"]
