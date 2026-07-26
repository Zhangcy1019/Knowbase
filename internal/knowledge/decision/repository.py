"""Atomic local persistence for Knowledge decision audit records."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from internal.knowledge.decision.models import KnowledgeDecisionRecord


class KnowledgeDecisionRepository:
    """Store audit records outside partition Git repositories."""

    def __init__(self, *, local_root: Path):
        self._root = local_root.expanduser().resolve() / "audit" / "decisions"
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, record: KnowledgeDecisionRecord) -> KnowledgeDecisionRecord:
        path = self._root / f"{record.decision_id}.json"
        payload = json.dumps(record.model_dump(mode="json"), ensure_ascii=False, indent=2)
        fd, temporary_name = tempfile.mkstemp(prefix=f".{record.decision_id}.", suffix=".tmp", dir=self._root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)
        return record

    def get(self, decision_id: str) -> KnowledgeDecisionRecord | None:
        path = self._root / f"{decision_id}.json"
        if not path.exists():
            return None
        return KnowledgeDecisionRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list(self, *, partition: str = "", status: str = "") -> list[KnowledgeDecisionRecord]:
        records = [
            KnowledgeDecisionRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self._root.glob("decision-*.json"))
        ]
        return [
            record
            for record in records
            if (not partition or record.partition == partition)
            and (not status or record.status == status)
        ]


__all__ = ["KnowledgeDecisionRepository"]
