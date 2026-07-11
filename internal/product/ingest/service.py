"""Product-facing ingest service."""

from __future__ import annotations

from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.models import (
    CaseEventPayload,
    CaseEventSnapshot,
    IngestRequest,
    IngestResult,
    KnowbaseEvent,
    KnowbaseEventType,
)
from internal.ports import CaseWritePort, EventPublisherPort, PartitionAccessPort
from internal.product.ingest.validator import KnowbaseIngestValidator


class KnowbaseIngestService:
    """Product-facing ingest service."""

    def __init__(
        self,
        *,
        validator: KnowbaseIngestValidator,
        draft_builder: KnowbaseCaseDraftBuilder,
        case_write_service: CaseWritePort,
        event_publisher: EventPublisherPort,
        partition_service: PartitionAccessPort,
        semantic_profile_extractor: KnowbaseSemanticProfileExtractor | None = None,
        summary_extractor: KnowbaseCaseSummaryExtractor | None = None,
        facet_resolver: KnowbaseCaseFacetResolver | None = None,
    ):
        self._validator = validator
        self._draft_builder = draft_builder
        self._case_write_service = case_write_service
        self._event_publisher = event_publisher
        self._partition_service = partition_service
        self._semantic_profile_extractor = semantic_profile_extractor or KnowbaseSemanticProfileExtractor()
        self._summary_extractor = summary_extractor or KnowbaseCaseSummaryExtractor()
        self._facet_resolver = facet_resolver or KnowbaseCaseFacetResolver()

    async def ingest(self, request: IngestRequest) -> IngestResult:
        request = self._validator.validate(request)
        partition = self._partition_service.get_partition(request.partition_name)
        if partition is None:
            raise ValueError(f"unknown partition: {request.partition_name}")
        if partition.status != "active":
            raise ValueError(f"partition is not active: {request.partition_name}")
        facet_definitions = self._partition_service.list_facet_definitions(request.partition_name)
        semantic_index = self._partition_service.get_semantic_index(request.partition_name)
        draft = self._draft_builder.build(request)
        draft.summary_text = await self._summary_extractor.extract(
            title=draft.title,
            source_content=draft.source_content,
        )
        draft.semantic_profile = await self._semantic_profile_extractor.extract(
            title=draft.title,
            source_content=draft.source_content,
            facet_definitions=facet_definitions,
            semantic_index=semantic_index,
        )
        draft.facets = self._facet_resolver.project_from_semantic_profile(
            semantic_profile=draft.semantic_profile,
            facet_definitions=facet_definitions,
        )
        case_document = self._case_write_service.create_case(
            partition_name=draft.partition,
            title=draft.title,
            source_content=draft.source_content,
            source_refs=draft.source_refs,
            summary_text=draft.summary_text,
            semantic_profile=draft.semantic_profile,
            metadata=draft.metadata,
            facets=draft.facets,
        )
        publish_result = await self._event_publisher.publish(
            KnowbaseEvent(
                event_type=KnowbaseEventType.CASE_CREATED,
                partition=draft.partition,
                resource_type="case",
                resource_id=case_document.case_id,
                occurred_at=case_document.created_at,
                payload=CaseEventPayload(
                    change_kind="create",
                    after=CaseEventSnapshot(
                        title=case_document.title,
                        facet_count=sum(len(values) for values in case_document.facets.values()),
                        facets=case_document.facets,
                    ),
                    changed_fields=[
                        "title",
                        "source_content",
                        "source_refs",
                        "summary_text",
                        "semantic_profile",
                        "metadata",
                        "facets",
                    ],
                    observed_facets=case_document.facets,
                ),
            )
        )
        backlog_event_ids = []
        event_record = publish_result.get("event")
        event_id = getattr(event_record, "event_id", "")
        if event_id:
            backlog_event_ids.append(event_id)
        result = IngestResult(
            case_id=case_document.case_id,
            partition=draft.partition,
            accepted=True,
            processing_status="queued",
            backlog_event_ids=backlog_event_ids,
            draft=draft,
        )
        result.facet_resolution_summary = (
            "facets were projected from semantic_profile under the current stable facet schema."
        )
        result.resolved_facets = case_document.facets
        return result
