"""Application-facing version-control capabilities."""

from __future__ import annotations

from typing import Protocol

from internal.models.version_control import VersionCommit, VersionControlStatus


class VersionControlPort(Protocol):
    """Operate on a versioned local workspace without exposing Git details."""

    def initialize(self) -> str:
        ...

    def status(self) -> VersionControlStatus:
        ...

    def current_revision(self) -> str:
        ...

    def diff(self, *, paths: list[str] | None = None) -> str:
        ...

    def commit(self, *, message: str, paths: list[str]) -> VersionCommit:
        ...

    def restore(self, *, revision: str, paths: list[str]) -> None:
        ...


__all__ = ["VersionControlPort"]
