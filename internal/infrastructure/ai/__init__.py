"""Shared AI infrastructure for chat completion and embeddings."""

from internal.infrastructure.ai.embedding import (
    EmbeddingConfig,
    OpenAICompatibleEmbeddingProvider,
)
from internal.infrastructure.ai.embedding_contracts import EmbeddingProvider
from internal.infrastructure.ai.generation import build_openai_client, generate_structured, generate_text
from internal.infrastructure.ai.embedding_service import create_embedding_provider
from internal.infrastructure.ai.openai_client import (
    DefaultOpenAIClient,
    OpenAIChatRequest,
    OpenAIChatResponse,
    OpenAIClientPort,
    OpenAIResponseFormat,
)

__all__ = [
    "EmbeddingConfig",
    "EmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "create_embedding_provider",
    "generate_text",
    "generate_structured",
    "build_openai_client",
    "OpenAIResponseFormat",
    "OpenAIChatRequest",
    "OpenAIChatResponse",
    "OpenAIClientPort",
    "DefaultOpenAIClient",
]
