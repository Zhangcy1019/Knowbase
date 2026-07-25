"""Cross-module ports for Knowledge batch notifications."""

from __future__ import annotations

from typing import Any, Protocol

class KnowledgeBatchNotificationPort(Protocol):
    """Notify Knowledge that a backlog batch is ready for maintenance."""

    async def notify_batch(self, *, batch) -> None:
        ...


__all__ = [
    "KnowledgeBatchNotificationPort",
]
