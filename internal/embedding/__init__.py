"""Embedding capabilities for knowbase ingest and query flows."""

from internal.embedding.contracts import EmbeddingProvider
from internal.embedding.provider import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
    load_embedding_config_from_env,
)
from internal.embedding.service import create_embedding_provider

__all__ = [
    "EmbeddingConfig",
    "EmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "load_embedding_config_from_env",
    "create_embedding_provider",
]
