"""Ingest request/result schemas for knowbase."""

from __future__ import annotations

from pydantic import BaseModel, Field

from internal.models.case import KnowbaseCaseDraft
from internal.models.facet import CaseFacetProfile


class IngestRequest(BaseModel):
    """External ingest request accepted by the knowbase product interface."""

    title: str = ""
    source_content: str = ""
    source_refs: list[str] = Field(default_factory=list)
    partition_name: str = ""
    author: str = ""
    source: str = "user"


class IngestResult(BaseModel):
    """Result returned after one ingest operation."""

    case_id: str = ""
    partition: str = ""
    accepted: bool = True
    processing_status: str = "queued"
    backlog_event_id: str = ""
    draft: KnowbaseCaseDraft | None = None
    facet_resolution_summary: str = ""
    resolved_facets: CaseFacetProfile = Field(default_factory=CaseFacetProfile)
