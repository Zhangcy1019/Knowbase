"""Commit policies shared by ingestion and Knowledge governance."""

from __future__ import annotations

from internal.models.version_control import VersionCommit
from internal.ports.version_control import VersionControlPort


class VersionCommitCoordinator:
    """Define commit boundaries without depending on Git directly."""

    def __init__(self, *, version_control: VersionControlPort):
        self._version_control = version_control

    def begin_governance(self) -> str:
        status = self._version_control.status()
        if not status.clean:
            raise RuntimeError("Knowledge governance requires a clean working tree")
        return status.revision

    def commit_case_ingest(self, *, paths: list[str], case_id: str) -> VersionCommit:
        return self._version_control.commit(
            message=f"ingest: add or update case {case_id}",
            paths=paths,
        )

    def commit_knowledge_governance(self, *, paths: list[str], partition: str) -> VersionCommit:
        return self._version_control.commit(
            message=f"knowledge: update partition {partition}",
            paths=paths,
        )


__all__ = ["VersionCommitCoordinator"]
