"""Local filesystem-backed persistence implementations."""

from __future__ import annotations

import json
import math
import fcntl
import hashlib
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from internal.infrastructure.persistence.types import PersistenceBundle
from internal.models import EventRecord, KnowbaseCaseDocument, KnowbaseCaseSearchExplain, KnowbaseCaseSearchHit, KnowbaseCaseSearchQuery, PartitionDocument
from internal.models.facet import PartitionFacetIndex, PartitionFacetIndexDocument, PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument
from internal.models.run import AgentRun, RunArtifact, RunStep
from internal.knowledge.statistics.models import StatisticsSnapshot
from internal.utils.config import RuntimeConfig


class _JsonDirectoryStore:
    def __init__(self, root: Path):
        self._root = root
        self._root.mkdir(parents=True, exist_ok=True)

    def create_index(self) -> dict[str, Any]:
        self._root.mkdir(parents=True, exist_ok=True)
        return {"acknowledged": True, "index": str(self._root), "created": True}

    def save_model(self, doc_id: str, model: Any) -> Any:
        path = self._root / f"{doc_id}.json"
        path.write_text(json.dumps(model.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
        return model

    def load_model(self, doc_id: str, model_cls):
        path = self._root / f"{doc_id}.json"
        if not path.exists():
            return None
        return model_cls.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def delete(self, doc_id: str) -> None:
        path = self._root / f"{doc_id}.json"
        if path.exists():
            path.unlink()

    def list_models(self, model_cls) -> list[Any]:
        documents: list[Any] = []
        for path in sorted(self._root.glob("*.json")):
            documents.append(model_cls.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        return documents


class PartitionRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "partitions")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def upsert(self, document: PartitionDocument) -> PartitionDocument:
        return self._store.save_model(document.partition_name, document)

    def list_documents(self) -> list[PartitionDocument]:
        return self._store.list_models(PartitionDocument)

    def get(self, partition_name: str) -> PartitionDocument | None:
        return self._store.load_model(partition_name, PartitionDocument)

    def delete(self, partition_name: str) -> dict[str, Any]:
        self._store.delete(partition_name)
        return {"acknowledged": True}


class PartitionFacetSchemaRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "partition_facet_schemas")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def upsert(self, document: PartitionFacetSchemaDocument) -> PartitionFacetSchemaDocument:
        return self._store.save_model(document.partition_name, document)

    def get(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        return self._store.load_model(partition_name, PartitionFacetSchemaDocument)

    def get_or_create(self, partition_name: str) -> PartitionFacetSchemaDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionFacetSchemaDocument(partition_name=partition_name, created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        self._store.delete(partition_name)
        return {"acknowledged": True}


class PartitionFacetIndexRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "partition_facet_indices")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def upsert(self, document: PartitionFacetIndexDocument) -> PartitionFacetIndexDocument:
        return self._store.save_model(document.partition_name, document)

    def get(self, partition_name: str) -> PartitionFacetIndexDocument | None:
        return self._store.load_model(partition_name, PartitionFacetIndexDocument)

    def get_or_create(self, partition_name: str) -> PartitionFacetIndexDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionFacetIndexDocument(partition_name=partition_name, facet_index=PartitionFacetIndex(partition_name=partition_name), created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        self._store.delete(partition_name)
        return {"acknowledged": True}


class PartitionSemanticIndexRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "partition_semantic_indices")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def upsert(self, document: PartitionSemanticIndexDocument) -> PartitionSemanticIndexDocument:
        return self._store.save_model(document.partition_name, document)

    def get(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        return self._store.load_model(partition_name, PartitionSemanticIndexDocument)

    def get_or_create(self, partition_name: str) -> PartitionSemanticIndexDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionSemanticIndexDocument(partition_name=partition_name, semantic_index=PartitionSemanticIndex(partition_name=partition_name), created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        self._store.delete(partition_name)
        return {"acknowledged": True}


class StatisticsSnapshotRepository:
    """Persist the current statistics snapshot for a partition."""

    def __init__(self, root: Path, *, directory: str = "knowledge_statistics"):
        self._root = root / directory

    @contextmanager
    def lock(self, partition: str):
        """Serialize read-modify-write operations for one partition."""
        partition_root = self._root / partition
        partition_root.mkdir(parents=True, exist_ok=True)
        lock_root = Path(tempfile.gettempdir()) / "knowbase-statistics-locks"
        lock_root.mkdir(parents=True, exist_ok=True)
        lock_key = hashlib.sha256(
            f"{self._root.resolve()}:{partition}".encode("utf-8")
        ).hexdigest()
        lock_path = lock_root / f"{lock_key}.lock"
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def get(self, partition: str) -> StatisticsSnapshot | None:
        path = self._root / partition / "snapshot.json"
        if not path.exists():
            return None
        return StatisticsSnapshot.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def upsert(self, snapshot: StatisticsSnapshot) -> StatisticsSnapshot:
        partition_root = self._root / snapshot.partition
        partition_root.mkdir(parents=True, exist_ok=True)
        path = partition_root / "snapshot.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)
        return snapshot


class KnowbaseCaseRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "cases")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def upsert(self, document: KnowbaseCaseDocument) -> KnowbaseCaseDocument:
        return self._store.save_model(document.case_id, document)

    def get(self, case_id: str) -> KnowbaseCaseDocument | None:
        return self._store.load_model(case_id, KnowbaseCaseDocument)

    def delete(self, case_id: str) -> dict[str, Any]:
        self._store.delete(case_id)
        return {"acknowledged": True}

    def get_many(self, case_ids: list[str]) -> list[KnowbaseCaseDocument]:
        return [document for case_id in case_ids if (document := self.get(case_id)) is not None]

    def list_by_partition(self, partition: str, *, size: int = 500) -> list[KnowbaseCaseDocument]:
        return [document for document in self._store.list_models(KnowbaseCaseDocument) if document.partition == partition][:size]

    def search_lexical(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        documents = self._filter_documents(query=query)
        ranked: list[tuple[float, KnowbaseCaseDocument]] = []
        needle = query.text.strip().lower()
        for document in documents:
            haystack = " ".join([document.title, document.summary_text, document.search_text, document.source_content]).lower()
            score = float(haystack.count(needle)) if needle else 1.0
            if needle and score <= 0:
                continue
            ranked.append((score or 1.0, document))
        ranked.sort(key=lambda item: (-item[0], item[1].updated_at or datetime.min.replace(tzinfo=timezone.utc)))
        return [self._to_hit(document=item[1], score=item[0]) for item in ranked[: query.size]]

    def search_vector(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        if not query.embedding:
            return []
        documents = self._filter_documents(query=query)
        ranked: list[tuple[float, KnowbaseCaseDocument]] = []
        for document in documents:
            if not document.search_vector:
                continue
            score = _cosine_similarity(query.embedding, document.search_vector)
            ranked.append((score, document))
        ranked.sort(key=lambda item: -item[0])
        return [self._to_hit(document=item[1], score=item[0]) for item in ranked[: query.size]]

    def _filter_documents(self, *, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseDocument]:
        documents = self._store.list_models(KnowbaseCaseDocument)
        filtered: list[KnowbaseCaseDocument] = []
        for document in documents:
            if query.case_ids and document.case_id not in query.case_ids:
                continue
            if query.partition_filters and document.partition not in query.partition_filters:
                continue
            if not _match_facet_filters(document=document, facet_filters=query.facet_filters):
                continue
            filtered.append(document)
        return filtered

    @staticmethod
    def _to_hit(*, document: KnowbaseCaseDocument, score: float) -> KnowbaseCaseSearchHit:
        return KnowbaseCaseSearchHit(case_id=document.case_id, score=score, partition=document.partition, title=document.title, summary_text=document.summary_text, source_excerpt=document.source_content[:240], facets=document.facets, explain=KnowbaseCaseSearchExplain(base_score=score, final_score=score), document=document.model_dump(mode="json"))


class EventRecordRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "events")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def save(self, record: EventRecord) -> EventRecord:
        now = datetime.now(timezone.utc)
        persisted = record.model_copy(update={"event_id": record.event_id or f"event-{int(now.timestamp() * 1000)}", "created_at": record.created_at or now, "updated_at": now})
        return self._store.save_model(persisted.event_id, persisted)

    def get(self, event_id: str) -> EventRecord | None:
        normalized = event_id.strip()
        if not normalized:
            return None
        return self._store.load_model(normalized, EventRecord)

    def list(self, *, partition: str = "", status: str = "", event_type: str = "", size: int = 500) -> list[EventRecord]:
        records = self._store.list_models(EventRecord)
        filtered = []
        for record in records:
            if partition and record.partition != partition:
                continue
            if status and record.status != status:
                continue
            if event_type and record.event_type != event_type:
                continue
            filtered.append(record)
        filtered.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return filtered[:size]

    def delete(self, event_id: str) -> None:
        self._store.delete(event_id.strip())


class AgentRunRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "runs")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def save(self, run: AgentRun) -> AgentRun:
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(update={"run_id": run.run_id or f"run-{int(now.timestamp() * 1000)}", "created_at": run.created_at or now, "updated_at": now})
        return self._store.save_model(persisted.run_id, persisted)

    def get(self, run_id: str) -> AgentRun | None:
        return self._store.load_model(run_id, AgentRun)

    def list(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        runs = self._store.list_models(AgentRun)
        filtered = [run for run in runs if (not partition or run.partition == partition) and (not status or run.status == status)]
        filtered.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return filtered

    def delete(self, run_id: str) -> None:
        self._store.delete(run_id)


class RunStepRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "run_steps")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def save(self, step: RunStep) -> RunStep:
        now = datetime.now(timezone.utc)
        persisted = step.model_copy(update={"step_id": step.step_id or f"{step.run_id}:step:{step.index}:{int(now.timestamp() * 1000)}", "created_at": step.created_at or now})
        return self._store.save_model(persisted.step_id, persisted)

    def list_for_run(self, run_id: str) -> list[RunStep]:
        steps = [step for step in self._store.list_models(RunStep) if step.run_id == run_id]
        steps.sort(key=lambda item: (item.index, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))
        return steps

    def delete_for_run(self, run_id: str) -> None:
        for step in self.list_for_run(run_id):
            self._store.delete(step.step_id)


class RunArtifactRepository:
    def __init__(self, root: Path):
        self._store = _JsonDirectoryStore(root / "run_artifacts")

    def create_index(self) -> dict[str, Any]:
        return self._store.create_index()

    def save(self, artifact: RunArtifact) -> RunArtifact:
        now = datetime.now(timezone.utc)
        persisted = artifact.model_copy(update={"artifact_id": artifact.artifact_id or f"{artifact.run_id}:{artifact.artifact_type}:{int(now.timestamp() * 1000)}", "created_at": artifact.created_at or now, "updated_at": now})
        return self._store.save_model(persisted.artifact_id, persisted)

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        artifacts = [artifact for artifact in self._store.list_models(RunArtifact) if artifact.run_id == run_id]
        artifacts.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc))
        return artifacts

    def delete_for_run(self, run_id: str) -> None:
        for artifact in self.list_for_run(run_id):
            self._store.delete(artifact.artifact_id)


def _match_facet_filters(*, document: KnowbaseCaseDocument, facet_filters: list[str]) -> bool:
    for facet_filter in facet_filters:
        parts = [part.strip() for part in facet_filter.split("/") if part.strip()]
        partition = parts[0] if len(parts) >= 1 else ""
        key = parts[1] if len(parts) >= 2 else ""
        value = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) == 2 else "")
        if partition and document.partition != partition:
            return False
        if key and value and value not in document.facets.get(key, []):
            return False
    return True


def _cosine_similarity(lhs: list[float], rhs: list[float]) -> float:
    dot = sum(left * right for left, right in zip(lhs, rhs))
    lhs_norm = math.sqrt(sum(value * value for value in lhs))
    rhs_norm = math.sqrt(sum(value * value for value in rhs))
    if lhs_norm == 0.0 or rhs_norm == 0.0:
        return 0.0
    return dot / (lhs_norm * rhs_norm)


def build_local_persistence_bundle(*, runtime_cfg: RuntimeConfig) -> PersistenceBundle:
    root = Path(runtime_cfg.storage.local_root).expanduser()
    return PersistenceBundle(
        partition_repository=PartitionRepository(root=root),
        partition_facet_index_repository=PartitionFacetIndexRepository(root=root),
        partition_facet_schema_repository=PartitionFacetSchemaRepository(root=root),
        partition_semantic_index_repository=PartitionSemanticIndexRepository(root=root),
        case_repository=KnowbaseCaseRepository(root=root),
        event_record_repository=EventRecordRepository(root=root),
        run_repository=AgentRunRepository(root=root),
        step_repository=RunStepRepository(root=root),
        artifact_repository=RunArtifactRepository(root=root),
        statistics_snapshot_repository=StatisticsSnapshotRepository(root=root),
        query_statistics_snapshot_repository=StatisticsSnapshotRepository(
            root=root, directory="runtime_statistics/query"
        ),
    )
