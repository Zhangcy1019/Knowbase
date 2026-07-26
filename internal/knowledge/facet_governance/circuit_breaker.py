"""Knowledge circuit-breaker skeleton."""

from __future__ import annotations


class KnowledgeCircuitBreaker:
    """Run deterministic fuse checks for knowledge patches and schema proposals."""

    def evaluate(self, *, partition: str, patch, metrics):
        raise NotImplementedError
