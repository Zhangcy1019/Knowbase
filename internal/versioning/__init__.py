"""Application-independent workspace versioning policies."""

from internal.versioning.commit_coordinator import MutationTransaction, VersionCommitCoordinator

__all__ = ["MutationTransaction", "VersionCommitCoordinator"]
