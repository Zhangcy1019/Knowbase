"""Case repository skeleton."""

from __future__ import annotations

from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from internal.connectors.es.knowbase import build_knowbase_es_client
from internal.models import KnowbaseCaseDocument, KnowbaseCaseSearchExplain, KnowbaseCaseSearchHit, KnowbaseCaseSearchQuery


class KnowbaseCaseRepository:
    """Persist and recall case documents."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "KnowbaseCaseRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_CASES_INDEX",
            default_index="ci_knowbase_cases_v1",
        )
        return cls(client=client, index_name=index_name)

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
        self._client.index_document(
            index=self._index_name,
            doc_id=document.case_id,
            document=payload,
            refresh="wait_for",
        )
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
        documents: list[KnowbaseCaseDocument] = []
        for case_id in case_ids:
            document = self.get(case_id)
            if document is not None:
                documents.append(document)
        return documents

    def list_by_partition(self, partition: str, *, size: int = 500) -> list[KnowbaseCaseDocument]:
        body = {
            "size": size,
            "query": {
                "bool": {
                    "filter": [
                        {"term": {"partition": partition}},
                    ]
                }
            },
        }
        response = self._client.search_raw(index=self._index_name, body=body)
        return [KnowbaseCaseDocument.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "case_id": {"type": "keyword"},
                    "partition": {"type": "keyword"},
                    "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "source_content": {"type": "text"},
                    "source_refs": {"type": "keyword"},
                    "summary_text": {"type": "text"},
                    "semantic_profile": {"type": "flattened"},
                    "metadata": {"type": "flattened"},
                    "facets": {"type": "flattened"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "search_text": {"type": "text"},
                    "search_vector": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"},
                    "content_vector": {"type": "dense_vector", "dims": 1024, "index": True, "similarity": "cosine"},
                }
            }
        }

    def build_lexical_search_body(self, query: KnowbaseCaseSearchQuery) -> dict[str, Any]:
        filters = self._build_common_filters(query)
        should: list[dict[str, Any]] = []

        if query.text.strip():
            should.append(
                {
                    "multi_match": {
                        "query": query.text,
                        "fields": [
                            "title^3",
                            "summary_text^3",
                            "search_text^2",
                            "source_content",
                        ],
                    }
                }
            )

        base_bool: dict[str, Any] = {"filter": filters}
        if should:
            base_bool["should"] = should
            base_bool["minimum_should_match"] = 1

        return {"size": query.size, "query": {"bool": base_bool}}

    def build_vector_search_body(self, query: KnowbaseCaseSearchQuery) -> dict[str, Any]:
        filters = self._build_common_filters(query)

        return {
            "size": query.size,
            "query": {
                "script_score": {
                    "query": {"bool": {"filter": filters}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'search_vector') + 1.0",
                        "params": {"query_vector": query.embedding},
                    },
                }
            },
        }

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
        return KnowbaseCaseSearchHit(
            case_id=str(source.get("case_id") or hit.get("_id") or ""),
            score=float(hit.get("_score") or 0.0),
            partition=str(source.get("partition") or ""),
            title=str(source.get("title") or ""),
            summary_text=str(source.get("summary_text") or ""),
            source_excerpt=excerpt,
            facets=dict(source.get("facets") or {}),
            explain=KnowbaseCaseSearchExplain(
                base_score=float(hit.get("_score") or 0.0),
                final_score=float(hit.get("_score") or 0.0),
            ),
            document=source,
        )
