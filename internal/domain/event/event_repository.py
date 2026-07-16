"""Persistent inbox repository for knowbase domain events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from internal.connectors.es.client import BaseElasticsearchClient
from internal.connectors.es.knowbase import build_knowbase_es_client
from internal.models import EventRecord


class EventRecordRepository:
    """Persist event inbox records into Elasticsearch."""

    def __init__(self, *, client: BaseElasticsearchClient, index_name: str):
        self._client = client
        self._index_name = index_name

    @classmethod
    def from_env(cls) -> "EventRecordRepository":
        client, index_name = build_knowbase_es_client(
            index_env="CIAGENT_KNOWBASE_EVENT_RECORDS_INDEX",
            default_index="ci_knowbase_event_records_v1",
        )
        return cls(client=client, index_name=index_name)

    def create_index(self) -> dict[str, Any]:
        if self._client.index_exists(index=self._index_name):
            return {"acknowledged": True, "index": self._index_name, "created": False}
        return self._client.create_index(index=self._index_name, body=self.build_index_mapping())

    def save(self, record: EventRecord) -> EventRecord:
        now = datetime.now(timezone.utc)
        persisted = record.model_copy(
            update={
                "event_id": record.event_id or f"event-{int(now.timestamp() * 1000)}",
                "created_at": record.created_at or now,
                "updated_at": now,
            }
        )
        payload = persisted.model_dump(mode="json")
        self._client.index_document(
            index=self._index_name,
            doc_id=persisted.event_id,
            document=payload,
            refresh="wait_for",
        )
        return persisted

    def get(self, event_id: str) -> EventRecord | None:
        normalized = event_id.strip()
        if not normalized:
            return None
        response = self._client.get_document_or_none(index=self._index_name, doc_id=normalized)
        if response is None:
            return None
        return EventRecord.model_validate(response.get("_source") or {})

    def list(
        self,
        *,
        partition: str = "",
        status: str = "",
        disposition: str = "",
        event_type: str = "",
        size: int = 500,
    ) -> list[EventRecord]:
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
        response = self._client.search_raw(
            index=self._index_name,
            body={"size": size, "query": query, "sort": [{"created_at": {"order": "desc"}}]},
        )
        return [EventRecord.model_validate(hit.get("_source") or {}) for hit in response.get("hits", {}).get("hits", [])]

    def delete(self, event_id: str) -> None:
        self._client.delete_document(index=self._index_name, doc_id=event_id.strip(), refresh="wait_for")

    @staticmethod
    def build_index_mapping() -> dict[str, Any]:
        return {
            "mappings": {
                "properties": {
                    "event_id": {"type": "keyword"},
                    "event_type": {"type": "keyword"},
                    "partition": {"type": "keyword"},
                    "resource_type": {"type": "keyword"},
                    "resource_id": {"type": "keyword"},
                    "payload": {"type": "flattened"},
                    "status": {"type": "keyword"},
                    "disposition": {"type": "keyword"},
                    "priority": {"type": "integer"},
                    "policy_id": {"type": "keyword"},
                    "ready_at": {"type": "date"},
                    "next_retry_at": {"type": "date"},
                    "last_run_at": {"type": "date"},
                    "run_id": {"type": "keyword"},
                    "batch_key": {"type": "keyword"},
                    "attempt_count": {"type": "integer"},
                    "error_message": {"type": "text"},
                    "occurred_at": {"type": "date"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "metadata": {"type": "flattened"},
                }
            }
        }
