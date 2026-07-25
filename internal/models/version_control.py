"""Shared version-control result models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VersionControlStatus:
    """Working-tree state observed before a coordinated change."""

    clean: bool
    revision: str
    changed_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class VersionCommit:
    """Result of one version-control commit."""

    revision: str
    message: str
    paths: list[str] = field(default_factory=list)


__all__ = ["VersionCommit", "VersionControlStatus"]
