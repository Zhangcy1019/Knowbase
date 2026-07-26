"""Commit policies shared by ingestion and Knowledge governance."""

from __future__ import annotations

from internal.models.version_control import VersionCommit
from internal.ports.version_control import VersionControlPort


class MutationTransaction:
    """Stage one workspace mutation and commit or restore it as a unit."""

    def __init__(self, *, version_control: VersionControlPort, message: str):
        self._version_control = version_control
        self.message = message
        status = version_control.status()
        if not status.clean:
            raise RuntimeError("versioned workspace must be clean before mutation")
        self.base_revision = status.revision
        self._paths: set[str] = set()
        self._closed = False

    def register_paths(self, paths: list[str]) -> None:
        self._paths.update(path for path in paths if path)

    def changed_paths(self) -> list[str]:
        return self._version_control.status().changed_paths

    def commit(self) -> VersionCommit:
        if self._closed:
            raise RuntimeError("version mutation transaction is already closed")
        paths = self.changed_paths()
        if self._paths:
            paths = sorted(set(paths).intersection(self._paths))
        if not paths:
            self._closed = True
            return VersionCommit(revision=self.base_revision, message=self.message, paths=[])
        result = self._version_control.commit(message=self.message, paths=paths)
        self._closed = True
        return result

    def rollback(self) -> None:
        if self._closed:
            return
        paths = sorted(self._paths)
        if paths:
            self._version_control.discard_untracked(paths=paths)
            self._version_control.restore(revision=self.base_revision, paths=paths)
        self._closed = True


class VersionCommitCoordinator:
    """Define workspace commit boundaries without depending on Git directly."""

    def __init__(self, *, version_control: VersionControlPort):
        self._version_control = version_control

    def begin_governance(self) -> str:
        status = self._version_control.status()
        if not status.clean:
            raise RuntimeError("Knowledge governance requires a clean working tree")
        return status.revision

    def begin_transaction(self, *, message: str) -> MutationTransaction:
        return MutationTransaction(version_control=self._version_control, message=message)

    def commit_case_ingest(self, *, paths: list[str], case_id: str) -> VersionCommit:
        return self._version_control.commit(message=f"ingest: add or update case {case_id}", paths=paths)

    def commit_knowledge_governance(
        self, *, paths: list[str] | None = None, partition: str
    ) -> VersionCommit:
        changed_paths = paths if paths is not None else self._version_control.status().changed_paths
        if not changed_paths:
            return VersionCommit(
                revision=self._version_control.current_revision(),
                message=f"knowledge: update partition {partition}",
                paths=[],
            )
        return self._version_control.commit(
            message=f"knowledge: update partition {partition}",
            paths=changed_paths,
        )


__all__ = ["MutationTransaction", "VersionCommitCoordinator"]
