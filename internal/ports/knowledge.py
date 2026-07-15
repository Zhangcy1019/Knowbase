"""Cross-module ports for knowledge-owned task shaping."""

from __future__ import annotations

from typing import Protocol

from internal.runtime.contracts import RuntimeRunRequest


class KnowledgeDispatchPort(Protocol):
    """Turn business-owned work batches into runtime requests."""

    def build_runtime_request(self, *, batch) -> RuntimeRunRequest:
        ...


__all__ = ["KnowledgeDispatchPort"]
