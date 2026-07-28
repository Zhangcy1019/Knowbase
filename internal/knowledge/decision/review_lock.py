"""Logical review locks that pause Knowledge drains per partition."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class PartitionReviewBlockedError(RuntimeError):
    """Raised when a partition is frozen by an unresolved review decision."""

    def __init__(self, *, partition: str, decision_id: str):
        self.partition = partition
        self.decision_id = decision_id
        super().__init__(
            f"partition already has a review decision: {partition} ({decision_id})"
        )


class PartitionReviewLock:
    """Persist one review lock per partition outside Git."""

    def __init__(self, *, local_root: Path):
        # use file system to persist review locks
        self._root = local_root.expanduser().resolve() / "audit" / "review_locks"
        self._root.mkdir(parents=True, exist_ok=True)

    def get(self, *, partition: str) -> dict[str, str] | None:
        path = self._path(partition)
        if not path.exists():
            return None
        return dict(json.loads(path.read_text(encoding="utf-8")))

    def acquire(self, *, partition: str, decision_id: str) -> None:
        existing = self.get(partition=partition)
        if existing is not None and existing.get("decision_id") != decision_id:
            raise PartitionReviewBlockedError(
                partition=partition,
                decision_id=str(existing.get("decision_id") or "unknown"),
            )
        self._write(
            partition=partition,
            payload={
                "partition": partition,
                "decision_id": decision_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    def release(self, *, partition: str, decision_id: str | None = None) -> None:
        existing = self.get(partition=partition)
        if existing is None:
            return
        if decision_id is not None and existing.get("decision_id") != decision_id:
            raise RuntimeError(f"review lock belongs to another decision: {partition}")
        self._path(partition).unlink(missing_ok=True)

    def _path(self, partition: str) -> Path:
        return self._root / f"{partition}.json"

    def _write(self, *, partition: str, payload: dict[str, str]) -> None:
        target = self._path(partition)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{partition}.", suffix=".tmp", dir=self._root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, target)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)


__all__ = ["PartitionReviewBlockedError", "PartitionReviewLock"]
