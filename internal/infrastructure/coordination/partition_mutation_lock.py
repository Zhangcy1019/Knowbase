"""Cross-process lock for partition file and Git mutations."""

from __future__ import annotations

import fcntl
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from uuid import uuid4


class PartitionMutationLock:
    """Hold an OS-level exclusive lock for one partition mutation."""

    def __init__(self, *, local_root: Path, partition: str, operation_id: str | None = None):
        self._locks_root = local_root.expanduser().resolve() / "locks"
        self._partition = str(partition).strip()
        self._operation_id = operation_id or f"op-{uuid4().hex}"
        self._handle = None
        self._metadata_path = self._locks_root / f"{self._partition}.json"

    def __enter__(self) -> "PartitionMutationLock":
        self.acquire()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()

    def acquire(self) -> None:
        if self._handle is not None:
            raise RuntimeError("partition mutation lock is already held")
        self._locks_root.mkdir(parents=True, exist_ok=True)
        lock_path = self._locks_root / f"{self._partition}.lock"
        handle = lock_path.open("a+", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        self._handle = handle
        self._metadata_path.write_text(
            json.dumps(
                {
                    "partition": self._partition,
                    "operation_id": self._operation_id,
                    "pid": os.getpid(),
                    "acquired_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def release(self) -> None:
        if self._handle is None:
            return
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
            if self._metadata_path.exists():
                self._metadata_path.unlink()


__all__ = ["PartitionMutationLock"]
