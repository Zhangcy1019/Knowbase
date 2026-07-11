"""Cross-module ports for product-facing use cases."""

from __future__ import annotations

from typing import Protocol

from internal.models import IngestRequest, IngestResult, QueryRequest, QueryResult


class IngestUseCase(Protocol):
    """Stable product ingest use case exposed to API routes."""

    async def ingest(self, request: IngestRequest) -> IngestResult:
        ...


class QueryUseCase(Protocol):
    """Stable product query use case exposed to API routes."""

    async def run(self, request: QueryRequest) -> QueryResult:
        ...


__all__ = [
    "IngestUseCase",
    "QueryUseCase",
]
