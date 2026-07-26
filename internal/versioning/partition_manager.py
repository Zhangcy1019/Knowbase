"""Partition-scoped Git repository and transaction management."""

from __future__ import annotations

import re
from pathlib import Path

from internal.infrastructure.version_control.git import GitRepository
from internal.versioning.commit_coordinator import VersionCommitCoordinator


_PARTITION_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class PartitionVersioningManager:
    """Resolve one dedicated Git workspace per partition."""

    def __init__(self, *, local_root: Path):
        self._local_root = local_root.expanduser().resolve()
        self._partitions_root = self._local_root / "partitions"

    @property
    def local_root(self) -> Path:
        return self._local_root

    def partition_root(self, partition: str) -> Path:
        normalized = self._validate_partition(partition)
        return self._partitions_root / normalized

    def repository(self, partition: str) -> GitRepository:
        return GitRepository(root=self.partition_root(partition))

    def coordinator(self, partition: str) -> VersionCommitCoordinator:
        return VersionCommitCoordinator(version_control=self.repository(partition))

    def prepare(self, partition: str) -> VersionCommitCoordinator:
        """Initialize/validate a clean partition repository before mutation."""
        self.initialize_partition(partition)
        return self.coordinator(partition)

    def initialize_partition(self, partition: str) -> str:
        """Initialize or validate a partition repository and return its revision."""
        return self.repository(partition).initialize()

    @staticmethod
    def _validate_partition(partition: str) -> str:
        normalized = str(partition).strip()
        if not _PARTITION_NAME.fullmatch(normalized):
            raise ValueError(
                "partition name must contain only letters, digits, '.', '_' or '-' "
                "and must not start with punctuation"
            )
        return normalized


__all__ = ["PartitionVersioningManager"]
