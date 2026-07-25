"""Knowledge patch application capability."""

from __future__ import annotations


class KnowledgePatchApplier:
    """Apply and roll back patch file changes without owning version control."""

    def apply(self, *, patch):
        raise NotImplementedError

    def rollback(self, *, patch) -> None:
        raise NotImplementedError


__all__ = ["KnowledgePatchApplier"]
