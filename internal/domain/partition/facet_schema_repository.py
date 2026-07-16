"""Repository for partition facet schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from internal.connectors.es.knowbase import build_knowbase_es_client
from internal.models.facet import PartitionFacetSchemaDocument


class PartitionFacetSchemaRepository:
    """Persist and load partition facet schemas."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "PartitionFacetSchemaRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_PARTITION_FACET_SCHEMAS_INDEX",
            default_index="ci_knowbase_partition_facet_schemas_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def upsert(self, document: PartitionFacetSchemaDocument) -> PartitionFacetSchemaDocument:
        self._client.index_document(
            index=self._index_name,
            doc_id=document.partition_name,
            document=document.model_dump(mode="json"),
            refresh="wait_for",
        )
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
        document = PartitionFacetSchemaDocument(
            partition_name=partition_name,
            created_at=now,
            updated_at=now,
        )
        return self.upsert(document)

    def delete(self, partition_name: str) -> dict[str, Any]:
        response = self._client.delete_document(index=self._index_name, doc_id=partition_name, refresh="wait_for")
        return response.body if hasattr(response, "body") else dict(response)

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "partition_name": {"type": "keyword"},
                    "facet_schema": {"type": "flattened"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                }
            }
        }
