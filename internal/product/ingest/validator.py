"""Ingest validator skeleton."""

from __future__ import annotations

from internal.models import IngestRequest


class KnowbaseIngestValidator:
    """Validate one ingest request before persistence."""

    def validate(self, request: IngestRequest) -> IngestRequest:
        if not request.partition_name.strip():
            raise ValueError("ingest partition_name must not be empty")
        if not request.source_content.strip():
            raise ValueError("ingest source_content must not be empty")
        return request
