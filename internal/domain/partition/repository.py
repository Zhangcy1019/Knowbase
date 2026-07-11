"""Partition repository skeleton."""

from __future__ import annotations

from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from _es import build_knowbase_es_client
from internal.models import PartitionDocument


class PartitionRepository:
    """Persist and load knowbase partitions."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "PartitionRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_PARTITIONS_INDEX",
            default_index="ci_knowbase_partitions_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionDocument) -> PartitionDocument:
        self._client.index_document(
            index=self._index_name,
            doc_id=document.partition_name,
            document=document.model_dump(mode="json"),
            refresh="wait_for",
        )
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
        return {
            "mappings": {
                "properties": {
                    "partition_name": {"type": "keyword"},
                    "scenario_description": {"type": "text"},
                    "status": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }
