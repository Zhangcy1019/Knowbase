"""Elasticsearch-backed persistence implementations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient, ElasticsearchConfig
from internal.infrastructure.persistence.types import PersistenceBundle
from internal.models import EventRecord, KnowbaseCaseDocument, KnowbaseCaseSearchExplain, KnowbaseCaseSearchHit, KnowbaseCaseSearchQuery, PartitionDocument
from internal.models.facet import PartitionFacetIndex, PartitionFacetIndexDocument, PartitionFacetSchemaDocument
from internal.models.partition_semantic_index import PartitionSemanticIndex, PartitionSemanticIndexDocument
from internal.models.run import AgentRun, RunArtifact, RunStep
from internal.utils.config import RuntimeConfig


def _build_client(*, url: str, api_key: str, index_name: str, verify_certs: bool) -> BaseElasticsearchClient:
    return BaseElasticsearchClient(
        ElasticsearchConfig(
            url=url,
            api_key=api_key,
            index=index_name,
            verify_certs=verify_certs,
        )
    )


class PartitionRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionDocument) -> PartitionDocument:
        self._client.index_document(index=self._index_name, doc_id=document.partition_name, document=document.model_dump(mode="json"), refresh="wait_for")
        return document

    def list_documents(self) -> list[PartitionDocument]:
        response = self._client.search_raw(index=self._index_name, body={"size": 200, "query": {"match_all": {}}})
        return [PartitionDocument.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def get(self, partition_name: str) -> PartitionDocument | None:
        response = self._client.get_document_or_none(index=self._index_name, doc_id=partition_name)
        if response is None:
            return None
        return PartitionDocument.model_validate(response.get("_source") or {})

    def delete(self, partition_name: str) -> dict[str, Any]:
        response = self._client.delete_document(index=self._index_name, doc_id=partition_name, refresh="wait_for")
        return response.body if hasattr(response, "body") else dict(response)

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"partition_name": {"type": "keyword"}, "scenario_description": {"type": "text"}, "status": {"type": "keyword"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}}}}


class PartitionFacetSchemaRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionFacetSchemaDocument) -> PartitionFacetSchemaDocument:
        self._client.index_document(index=self._index_name, doc_id=document.partition_name, document=document.model_dump(mode="json"), refresh="wait_for")
        return document

    def get(self, partition_name: str) -> PartitionFacetSchemaDocument | None:
        response = self._client.get_document_or_none(index=self._index_name, doc_id=partition_name)
        if response is None:
            return None
        return PartitionFacetSchemaDocument.model_validate(response.get("_source") or {})

    def get_or_create(self, partition_name: str) -> PartitionFacetSchemaDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionFacetSchemaDocument(partition_name=partition_name, created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        response = self._client.delete_document(index=self._index_name, doc_id=partition_name, refresh="wait_for")
        return response.body if hasattr(response, "body") else dict(response)

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"partition_name": {"type": "keyword"}, "facet_schema": {"type": "flattened"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}}}}


class PartitionFacetIndexRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionFacetIndexDocument) -> PartitionFacetIndexDocument:
        self._client.index_document(index=self._index_name, doc_id=document.partition_name, document=document.model_dump(mode="json"), refresh="wait_for")
        return document

    def get(self, partition_name: str) -> PartitionFacetIndexDocument | None:
        response = self._client.get_document_or_none(index=self._index_name, doc_id=partition_name)
        if response is None:
            return None
        return PartitionFacetIndexDocument.model_validate(response.get("_source") or {})

    def get_or_create(self, partition_name: str) -> PartitionFacetIndexDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionFacetIndexDocument(partition_name=partition_name, facet_index=PartitionFacetIndex(partition_name=partition_name), created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        response = self._client.delete_document(index=self._index_name, doc_id=partition_name, refresh="wait_for")
        return response.body if hasattr(response, "body") else dict(response)

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"partition_name": {"type": "keyword"}, "facet_index": {"type": "flattened"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}}}}


class PartitionSemanticIndexRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionSemanticIndexDocument) -> PartitionSemanticIndexDocument:
        self._client.index_document(index=self._index_name, doc_id=document.partition_name, document=document.model_dump(mode="json"), refresh="wait_for")
        return document

    def get(self, partition_name: str) -> PartitionSemanticIndexDocument | None:
        response = self._client.get_document_or_none(index=self._index_name, doc_id=partition_name)
        if response is None:
            return None
        return PartitionSemanticIndexDocument.model_validate(response.get("_source") or {})

    def get_or_create(self, partition_name: str) -> PartitionSemanticIndexDocument:
        existing = self.get(partition_name)
        if existing is not None:
            return existing
        now = datetime.now(timezone.utc)
        return self.upsert(PartitionSemanticIndexDocument(partition_name=partition_name, semantic_index=PartitionSemanticIndex(partition_name=partition_name), created_at=now, updated_at=now))

    def delete(self, partition_name: str) -> dict[str, Any]:
        response = self._client.delete_document(index=self._index_name, doc_id=partition_name, refresh="wait_for")
        return response.body if hasattr(response, "body") else dict(response)

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"partition_name": {"type": "keyword"}, "semantic_index": {"type": "flattened"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}}}}


class KnowbaseCaseRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: KnowbaseCaseDocument) -> KnowbaseCaseDocument:
        payload = document.model_dump(mode="json")
        if not payload.get("search_vector"):
            payload.pop("search_vector", None)
        if not payload.get("content_vector"):
            payload.pop("content_vector", None)
        self._client.index_document(index=self._index_name, doc_id=document.case_id, document=payload, refresh="wait_for")
        return document

    def get(self, case_id: str) -> KnowbaseCaseDocument | None:
        response = self._client.get_document_or_none(index=self._index_name, doc_id=case_id)
        if response is None:
            return None
        return KnowbaseCaseDocument.model_validate(response.get("_source") or {})

    def delete(self, case_id: str) -> dict[str, Any]:
        return self._client.delete_document(index=self._index_name, doc_id=case_id, refresh="wait_for")

    def search_lexical(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        response = self._client.search_raw(index=self._index_name, body=self.build_lexical_search_body(query))
        return [self._normalize_hit(hit) for hit in response.get("hits", {}).get("hits", [])]

    def search_vector(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        response = self._client.search_raw(index=self._index_name, body=self.build_vector_search_body(query))
        return [self._normalize_hit(hit) for hit in response.get("hits", {}).get("hits", [])]

    def get_many(self, case_ids: list[str]) -> list[KnowbaseCaseDocument]:
        return [document for case_id in case_ids if (document := self.get(case_id)) is not None]

    def list_by_partition(self, partition: str, *, size: int = 500) -> list[KnowbaseCaseDocument]:
        body = {"size": size, "query": {"bool": {"filter": [{"term": {"partition": partition}}]}}}
        response = self._client.search_raw(index=self._index_name, body=body)
        return [KnowbaseCaseDocument.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"case_id": {"type": "keyword"}, "partition": {"type": "keyword"}, "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}}, "source_content": {"type": "text"}, "source_refs": {"type": "keyword"}, "summary_text": {"type": "text"}, "semantic_profile": {"type": "flattened"}, "metadata": {"type": "flattened"}, "facets": {"type": "flattened"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}, "search_text": {"type": "text"}, "search_vector": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"}, "content_vector": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"}}}}

    def build_lexical_search_body(self, query: KnowbaseCaseSearchQuery) -> dict[str, Any]:
        filters = self._build_common_filters(query)
        should: list[dict[str, Any]] = []
        if query.text.strip():
            should.append({"multi_match": {"query": query.text, "fields": ["title^3", "summary_text^3", "search_text^2", "source_content"]}})
        base_bool: dict[str, Any] = {"filter": filters}
        if should:
            base_bool["should"] = should
            base_bool["minimum_should_match"] = 1
        return {"size": query.size, "query": {"bool": base_bool}}

    def build_vector_search_body(self, query: KnowbaseCaseSearchQuery) -> dict[str, Any]:
        filters = self._build_common_filters(query)
        return {"size": query.size, "query": {"script_score": {"query": {"bool": {"filter": filters}}, "script": {"source": "cosineSimilarity(params.query_vector, 'search_vector') + 1.0", "params": {"query_vector": query.embedding}}}}}

    @staticmethod
    def _build_common_filters(query: KnowbaseCaseSearchQuery) -> list[dict[str, Any]]:
        filters: list[dict[str, Any]] = []
        if query.case_ids:
            filters.append({"terms": {"case_id": query.case_ids}})
        if query.partition_filters:
            filters.append({"terms": {"partition": query.partition_filters}})
        for facet_filter in query.facet_filters:
            parts = [part.strip() for part in facet_filter.split("/") if part.strip()]
            partition = parts[0] if len(parts) >= 1 else ""
            key = parts[1] if len(parts) >= 2 else ""
            value = parts[2] if len(parts) >= 3 else (parts[1] if len(parts) == 2 else "")
            if partition:
                filters.append({"term": {"partition": partition}})
            if value:
                field_name = f"facets.{key}" if key and len(parts) >= 3 else "facets"
                filters.append({"term": {field_name: value}})
        return filters

    @staticmethod
    def _normalize_hit(hit: dict[str, Any]) -> KnowbaseCaseSearchHit:
        source = hit.get("_source") or {}
        excerpt = str(source.get("source_content") or "")[:240]
        return KnowbaseCaseSearchHit(case_id=str(source.get("case_id") or hit.get("_id") or ""), score=float(hit.get("_score") or 0.0), partition=str(source.get("partition") or ""), title=str(source.get("title") or ""), summary_text=str(source.get("summary_text") or ""), source_excerpt=excerpt, facets=dict(source.get("facets") or {}), explain=KnowbaseCaseSearchExplain(base_score=float(hit.get("_score") or 0.0), final_score=float(hit.get("_score") or 0.0)), document=source)


class EventRecordRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, record: EventRecord) -> EventRecord:
        now = datetime.now(timezone.utc)
        persisted = record.model_copy(update={"event_id": record.event_id or f"event-{int(now.timestamp() * 1000)}", "created_at": record.created_at or now, "updated_at": now})
        self._client.index_document(index=self._index_name, doc_id=persisted.event_id, document=persisted.model_dump(mode="json"), refresh="wait_for")
        return persisted

    def get(self, event_id: str) -> EventRecord | None:
        normalized = event_id.strip()
        if not normalized:
            return None
        response = self._client.get_document_or_none(index=self._index_name, doc_id=normalized)
        if response is None:
            return None
        return EventRecord.model_validate(response.get("_source") or {})

    def list(self, *, partition: str = "", status: str = "", disposition: str = "", event_type: str = "", size: int = 500) -> list[EventRecord]:
        filters: list[dict[str, Any]] = []
        if partition.strip():
            filters.append({"term": {"partition": partition.strip()}})
        if status.strip():
            filters.append({"term": {"status": status.strip()}})
        if disposition.strip():
            filters.append({"term": {"disposition": disposition.strip()}})
        if event_type.strip():
            filters.append({"term": {"event_type": event_type.strip()}})
        query: dict[str, Any] = {"bool": {"filter": filters}} if filters else {"match_all": {}}
        response = self._client.search_raw(index=self._index_name, body={"size": size, "query": query, "sort": [{"created_at": {"order": "desc"}}]})
        return [EventRecord.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete(self, event_id: str) -> None:
        self._client.delete_document(index=self._index_name, doc_id=event_id.strip(), refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"event_id": {"type": "keyword"}, "event_type": {"type": "keyword"}, "partition": {"type": "keyword"}, "resource_type": {"type": "keyword"}, "resource_id": {"type": "keyword"}, "payload": {"type": "flattened"}, "status": {"type": "keyword"}, "disposition": {"type": "keyword"}, "priority": {"type": "integer"}, "policy_id": {"type": "keyword"}, "ready_at": {"type": "date"}, "next_retry_at": {"type": "date"}, "last_run_at": {"type": "date"}, "run_id": {"type": "keyword"}, "batch_key": {"type": "keyword"}, "attempt_count": {"type": "integer"}, "error_message": {"type": "text"}, "occurred_at": {"type": "date"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}, "metadata": {"type": "flattened"}}}}


class AgentRunRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, run: AgentRun) -> AgentRun:
        now = datetime.now(timezone.utc)
        persisted = run.model_copy(update={"run_id": run.run_id or f"run-{int(now.timestamp() * 1000)}", "created_at": run.created_at or now, "updated_at": now})
        self._client.index_document(index=self._index_name, doc_id=persisted.run_id, document=persisted.model_dump(mode="json"), refresh="wait_for")
        return persisted

    def get(self, run_id: str) -> AgentRun | None:
        if not self._client.document_exists(index=self._index_name, doc_id=run_id):
            return None
        response = self._client.get_document(index=self._index_name, doc_id=run_id)
        return AgentRun.model_validate(response.get("_source") or {})

    def list(self, *, partition: str = "", status: str = "") -> list[AgentRun]:
        filters: list[dict[str, Any]] = []
        if partition:
            filters.append({"term": {"partition": partition}})
        if status:
            filters.append({"term": {"status": status}})
        query: dict[str, Any] = {"bool": {"filter": filters}} if filters else {"match_all": {}}
        response = self._client.search_raw(index=self._index_name, body={"size": 200, "query": query, "sort": [{"created_at": {"order": "desc"}}]})
        return [AgentRun.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete(self, run_id: str) -> None:
        self._client.delete_document(index=self._index_name, doc_id=run_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"run_id": {"type": "keyword"}, "partition": {"type": "keyword"}, "agent_id": {"type": "keyword"}, "mode": {"type": "keyword"}, "status": {"type": "keyword"}, "source_type": {"type": "keyword"}, "source_event_type": {"type": "keyword"}, "source_event_id": {"type": "keyword"}, "source_ref": {"type": "keyword"}, "objective": {"type": "text"}, "reasoning_summary": {"type": "text"}, "final_summary": {"type": "text"}, "planning_context": {"type": "flattened"}, "tool_whitelist": {"type": "keyword"}, "skill_whitelist": {"type": "keyword"}, "step_count": {"type": "integer"}, "tool_call_count": {"type": "integer"}, "skill_call_count": {"type": "integer"}, "max_steps": {"type": "integer"}, "max_tool_calls": {"type": "integer"}, "max_skill_calls": {"type": "integer"}, "risk_level": {"type": "keyword"}, "requires_review": {"type": "boolean"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}, "finished_at": {"type": "date"}}}}


class RunStepRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, step: RunStep) -> RunStep:
        now = datetime.now(timezone.utc)
        persisted = step.model_copy(update={"step_id": step.step_id or f"{step.run_id}:step:{step.index}:{int(now.timestamp() * 1000)}", "created_at": step.created_at or now})
        self._client.index_document(index=self._index_name, doc_id=persisted.step_id, document=persisted.model_dump(mode="json"), refresh="wait_for")
        return persisted

    def list_for_run(self, run_id: str) -> list[RunStep]:
        response = self._client.search_raw(index=self._index_name, body={"size": 500, "query": {"bool": {"filter": [{"term": {"run_id": run_id}}]}}, "sort": [{"index": {"order": "asc"}}, {"created_at": {"order": "asc"}}]})
        return [RunStep.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete_for_run(self, run_id: str) -> None:
        for step in self.list_for_run(run_id):
            self._client.delete_document(index=self._index_name, doc_id=step.step_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"step_id": {"type": "keyword"}, "run_id": {"type": "keyword"}, "index": {"type": "integer"}, "step_type": {"type": "keyword"}, "name": {"type": "keyword"}, "input": {"type": "flattened"}, "output": {"type": "flattened"}, "summary": {"type": "text"}, "created_at": {"type": "date"}}}}


class RunArtifactRepository:
    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, artifact: RunArtifact) -> RunArtifact:
        now = datetime.now(timezone.utc)
        persisted = artifact.model_copy(update={"artifact_id": artifact.artifact_id or f"{artifact.run_id}:{artifact.artifact_type}:{int(now.timestamp() * 1000)}", "created_at": artifact.created_at or now, "updated_at": now})
        self._client.index_document(index=self._index_name, doc_id=persisted.artifact_id, document=persisted.model_dump(mode="json"), refresh="wait_for")
        return persisted

    def list_for_run(self, run_id: str) -> list[RunArtifact]:
        response = self._client.search_raw(index=self._index_name, body={"size": 200, "query": {"bool": {"filter": [{"term": {"run_id": run_id}}]}}, "sort": [{"created_at": {"order": "asc"}}]})
        return [RunArtifact.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete_for_run(self, run_id: str) -> None:
        for artifact in self.list_for_run(run_id):
            self._client.delete_document(index=self._index_name, doc_id=artifact.artifact_id, refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {"mappings": {"properties": {"artifact_id": {"type": "keyword"}, "run_id": {"type": "keyword"}, "artifact_type": {"type": "keyword"}, "title": {"type": "text"}, "content": {"type": "flattened"}, "created_at": {"type": "date"}, "updated_at": {"type": "date"}}}}


def build_es_persistence_bundle(*, runtime_cfg: RuntimeConfig) -> PersistenceBundle:
    es_cfg = runtime_cfg.es
    return PersistenceBundle(
        partition_repository=PartitionRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.partitions_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.partitions_index),
        partition_facet_index_repository=PartitionFacetIndexRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.partition_facet_index_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.partition_facet_index_index),
        partition_facet_schema_repository=PartitionFacetSchemaRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.partition_facet_schemas_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.partition_facet_schemas_index),
        partition_semantic_index_repository=PartitionSemanticIndexRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.partition_semantic_index_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.partition_semantic_index_index),
        case_repository=KnowbaseCaseRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.cases_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.cases_index),
        event_record_repository=EventRecordRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.event_records_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.event_records_index),
        run_repository=AgentRunRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.agent_runs_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.agent_runs_index),
        step_repository=RunStepRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.run_steps_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.run_steps_index),
        artifact_repository=RunArtifactRepository(client=_build_client(url=es_cfg.url, api_key=es_cfg.api_key, index_name=es_cfg.run_artifacts_index, verify_certs=es_cfg.verify_certs), index_name=es_cfg.run_artifacts_index),
    )
