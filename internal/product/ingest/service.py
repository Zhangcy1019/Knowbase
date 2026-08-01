"""Product-facing ingest service."""

from __future__ import annotations

from uuid import uuid4

from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.models import (
    CaseEventSnapshot,
    IngestRequest,
    IngestResult,
    KnowbaseEvent,
    KnowbaseEventType,
)
from internal.knowledge.statistics import CaseObservation
from internal.infrastructure.coordination import PartitionMutationLockProvider
from internal.versioning.partition_manager import PartitionVersioningManager
from internal.ports import (
    CaseWritePort,
    EventPublisherPort,
    PartitionProfileReadPort,
    PartitionReadPort,
    PartitionTaskQueuePort,
)
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
        partition_service: PartitionReadPort | PartitionProfileReadPort,
        semantic_profile_extractor: KnowbaseSemanticProfileExtractor | None = None,
        summary_extractor: KnowbaseCaseSummaryExtractor | None = None,
        facet_resolver: KnowbaseCaseFacetResolver | None = None,
        statistics=None,
        versioning: PartitionVersioningManager | None = None,
        task_queue: PartitionTaskQueuePort | None = None,
        mutation_lock_provider: PartitionMutationLockProvider | None = None,
    ):
        self._validator = validator
        self._draft_builder = draft_builder
        self._case_write_service = case_write_service
        self._event_publisher = event_publisher
        self._partition_service = partition_service
        self._semantic_profile_extractor = semantic_profile_extractor or KnowbaseSemanticProfileExtractor()
        self._summary_extractor = summary_extractor or KnowbaseCaseSummaryExtractor()
        self._facet_resolver = facet_resolver or KnowbaseCaseFacetResolver()
        self._statistics = statistics
        self._versioning = versioning
        if task_queue is None:
            raise ValueError("KnowbaseIngestService requires a partition task queue")
        self._task_queue = task_queue
        self._mutation_lock_provider = mutation_lock_provider

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
        case_id = f"case-{uuid4().hex}"
        task = self._task_queue.enqueue(
            partition=draft.partition,
            kind="case_input",
            payload={"case_id": case_id},
            handler=lambda task: self._execute_case_input(task=task, case_id=case_id, draft=draft),
        )
        resolved_facets = draft.facets
        return IngestResult(
            case_id=case_id,
            task_id=task.task_id,
            partition=draft.partition,
            accepted=True,
            processing_status="queued",
            draft=draft,
            facet_resolution_summary=(
                "facets were projected from semantic_profile under the current stable facet schema."
            ),
            resolved_facets=resolved_facets,
        )

    async def _execute_case_input(self, *, task, case_id: str, draft) -> None:
        lock_context = (
            self._mutation_lock_provider.lock(draft.partition)
            if self._mutation_lock_provider is not None
            else _NullContext()
        )
        with lock_context:
            versioning = (
                self._versioning.prepare(draft.partition)
                if self._versioning is not None
                else None
            )
            case_document = self._case_write_service.create_case(
                case_id=case_id,
                partition_name=draft.partition,
                title=draft.title,
                source_content=draft.source_content,
                source_refs=draft.source_refs,
                summary_text=draft.summary_text,
                semantic_profile=draft.semantic_profile,
                metadata=draft.metadata,
                facets=draft.facets,
            )
            if self._statistics is not None:
                self._statistics.append_case_observation(
                    observation=CaseObservation(
                        observation_id=f"case:{case_document.case_id}",
                        partition=case_document.partition,
                        source_id=case_document.case_id,
                        facets=case_document.facets.model_dump(),
                        semantic_profile=case_document.semantic_profile.model_dump(),
                        metadata={"event": "case_created"},
                    )
                )
            if versioning is not None:
                versioning.commit_case_ingest(
                    case_id=case_document.case_id,
                    paths=[
                        f"cases/{case_document.case_id}.json",
                        "facet_index.json",
                        "semantic_index.json",
                    ],
                )
        await self._event_publisher.publish(
            KnowbaseEvent.for_case(
                event_type=KnowbaseEventType.CASE_CREATED,
                change_kind="create",
                partition=draft.partition,
                case_id=case_document.case_id,
                occurred_at=case_document.created_at,
                after=CaseEventSnapshot(
                    title=case_document.title,
                    facet_count=sum(len(values) for values in case_document.facets.values()),
                    facets=case_document.facets.model_dump(),
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
                observed_facets=case_document.facets.model_dump(),
            )
        )


class _NullContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return None
