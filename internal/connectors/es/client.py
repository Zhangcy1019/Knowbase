"""Elasticsearch client wrappers.

`BaseElasticsearchClient` exposes generic index/document/search operations.
`ElasticsearchClient` preserves the existing trace-oriented search API used by
current job-status and resolver code.
"""

from __future__ import annotations

import ssl
import time
from dataclasses import dataclass
from typing import Any

from internal.connectors.es.models import ESFieldFilter, ESTraceRecord
from internal.utils.logger import get_logger

try:
    from elasticsearch import Elasticsearch
except ImportError:  # pragma: no cover - guarded in runtime
    Elasticsearch = None  # type: ignore[assignment]


logger = get_logger(__name__)


@dataclass(frozen=True)
class ElasticsearchConfig:
    url: str
    api_key: str
    index: str
    verify_certs: bool = True


class BaseElasticsearchClient:
    """Generic Elasticsearch client wrapper."""

    def __init__(self, config: ElasticsearchConfig, client: Any | None = None):
        self.config = config
        if client is not None:
            self._client = client
            return

        if Elasticsearch is None:
            raise RuntimeError(
                "elasticsearch package is required. Install with `pip install elasticsearch`."
            )

        self._client = Elasticsearch(
            self.config.url,
            api_key=self.config.api_key,
            ssl_version=ssl.TLSVersion.TLSv1_2,
            verify_certs=self.config.verify_certs,
        )

    def search_raw(self, *, body: dict[str, Any], index: str | None = None) -> dict[str, Any]:
        """Execute a raw ES search request."""
        target_index = index or self.config.index
        logger.debug("Executing raw ES search", extra={"index": target_index})
        return self._client.search(index=target_index, body=body)

    def index_document(
        self,
        *,
        document: dict[str, Any],
        doc_id: str | None = None,
        index: str | None = None,
        refresh: str | bool | None = None,
    ) -> dict[str, Any]:
        """Index a document into Elasticsearch."""
        kwargs: dict[str, Any] = {"index": index or self.config.index, "document": document}
        if doc_id is not None:
            kwargs["id"] = doc_id
        if refresh is not None:
            kwargs["refresh"] = refresh
        return self._client.index(**kwargs)

    def get_document(self, *, doc_id: str, index: str | None = None) -> dict[str, Any]:
        """Get one document by id."""
        return self._client.get(index=index or self.config.index, id=doc_id)

    def get_document_or_none(self, *, doc_id: str, index: str | None = None) -> dict[str, Any] | None:
        """Get one document by id, returning None when the document does not exist."""
        try:
            return self.get_document(doc_id=doc_id, index=index)
        except Exception as exc:  # noqa: BLE001
            error_type = type(exc).__name__
            status_code = getattr(exc, "status_code", None)
            if error_type == "NotFoundError" or status_code == 404:
                return None
            raise

    def document_exists(self, *, doc_id: str, index: str | None = None) -> bool:
        """Check whether a document exists."""
        return bool(self._client.exists(index=index or self.config.index, id=doc_id))

    def delete_document(
        self,
        *,
        doc_id: str,
        index: str | None = None,
        refresh: str | bool | None = None,
    ) -> dict[str, Any]:
        """Delete one document by id."""
        kwargs: dict[str, Any] = {"index": index or self.config.index, "id": doc_id}
        if refresh is not None:
            kwargs["refresh"] = refresh
        return self._client.delete(**kwargs)

    def index_exists(self, *, index: str | None = None) -> bool:
        """Check whether an index exists."""
        return bool(self._client.indices.exists(index=index or self.config.index))

    def create_index(self, *, body: dict[str, Any], index: str | None = None) -> dict[str, Any]:
        """Create an index with mapping/settings."""
        return self._client.indices.create(index=index or self.config.index, **body)

    def get_index_mapping(self, *, index: str | None = None) -> dict[str, Any]:
        """Get index mapping."""
        return self._client.indices.get_mapping(index=index or self.config.index)

    def delete_index(self, *, index: str | None = None, ignore_unavailable: bool = True) -> dict[str, Any]:
        """Delete an index."""
        return self._client.indices.delete(index=index or self.config.index, ignore_unavailable=ignore_unavailable)


class ElasticsearchClient(BaseElasticsearchClient):
    """Trace-oriented Elasticsearch client preserving the existing contract."""

    def search(
        self,
        *,
        filters: list[ESFieldFilter],
        size: int,
        time_field: str = "timestamp",
    ) -> list[ESTraceRecord]:
        query = self._build_query(filters=filters, size=size, time_field=time_field)
        logger.debug(
            "Executing ES search",
            extra={
                "index": self.config.index,
                "batch_size": size,
                "time_field": time_field,
            },
        )
        response = self.search_raw(body=query)
        hits = response.get("hits", {}).get("hits", [])

        records: list[ESTraceRecord] = []
        for hit in hits:
            doc_id = str(hit.get("_id", ""))
            sort_values = hit.get("sort", [])
            source = hit.get("_source", {}) or {}
            if sort_values and len(sort_values) >= 1:
                timestamp_ms = int(sort_values[0])
            else:
                timestamp_ms = int(source.get(time_field, 0))
            records.append(ESTraceRecord(doc_id=doc_id, timestamp_ms=timestamp_ms, source=source))

        logger.debug("ES search completed", extra={"record_count": len(records)})
        return records

    def _build_query(
        self,
        *,
        filters: list[ESFieldFilter],
        size: int,
        time_field: str,
    ) -> dict[str, Any]:
        must_filters: list[dict[str, Any]] = []
        should_filters: list[dict[str, Any]] = []

        for filter_item in filters:
            if filter_item.match_values:
                if len(filter_item.match_values) == 1 and filter_item.match_values[0] == "*":
                    filter_query = {"exists": {"field": filter_item.field}}
                elif len(filter_item.match_values) == 1:
                    filter_query = {"term": {filter_item.field: filter_item.match_values[0]}}
                else:
                    filter_query = {"terms": {filter_item.field: filter_item.match_values}}

                if filter_item.filter_type == "must":
                    must_filters.append(filter_query)
                else:
                    should_filters.append(filter_query)

            if filter_item.start_time_ms is not None or filter_item.end_time_ms is not None:
                range_filter: dict[str, Any] = {"format": "epoch_millis"}
                if filter_item.start_time_ms is not None:
                    range_filter["gte"] = filter_item.start_time_ms
                if filter_item.end_time_ms is not None:
                    range_filter["lte"] = filter_item.end_time_ms
                must_filters.append({"range": {filter_item.field: range_filter}})

        if not any(f.get("range", {}).get(time_field) for f in must_filters):
            must_filters.append(
                {
                    "range": {
                        time_field: {
                            "lte": int(time.time() * 1000),
                            "format": "epoch_millis",
                        }
                    }
                }
            )

        bool_query: dict[str, Any] = {"must": must_filters}
        if should_filters:
            bool_query["should"] = should_filters
            bool_query["minimum_should_match"] = 1

        return {
            "query": {"bool": bool_query},
            "size": size,
            "sort": [{time_field: {"order": "asc"}}],
        }
