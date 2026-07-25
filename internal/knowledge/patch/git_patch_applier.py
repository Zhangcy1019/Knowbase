"""Git-backed knowledge patch applier skeleton."""

from __future__ import annotations


class GitKnowledgePatchApplier:
    """Apply and rollback knowledge patches through a git-backed working tree."""

    def apply(self, *, patch):
        raise NotImplementedError

    def rollback(self, *, patch) -> None:
        raise NotImplementedError
