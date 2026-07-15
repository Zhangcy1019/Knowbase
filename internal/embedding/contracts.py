"""Contracts for knowledge embedding providers."""

from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    """Stable embedding interface used by ingest and query flows."""

    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


__all__ = ["EmbeddingProvider"]
