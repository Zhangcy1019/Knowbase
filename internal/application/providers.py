"""Provider helpers for assembling core knowbase services."""

from __future__ import annotations

from dataclasses import dataclass

from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.domain.case.repository import KnowbaseCaseRepository
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.service import KnowbaseCaseService
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.domain.case.write_service import KnowbaseCaseWriteService
from internal.domain.event.event_repository import EventRecordRepository
from internal.domain.event.inbox_service import KnowbaseEventInboxService
from internal.domain.event.publisher import KnowbaseEventPublisher
from internal.domain.partition.facet_index_repository import PartitionFacetIndexRepository
from internal.domain.partition.facet_schema_repository import PartitionFacetSchemaRepository
from internal.domain.partition.repository import PartitionRepository
from internal.domain.partition.schema_suggester import PartitionSchemaSuggester
from internal.domain.partition.semantic_index_repository import PartitionSemanticIndexRepository
from internal.domain.partition.service import PartitionService
from internal.domain.run.artifact_repository import RunArtifactRepository
from internal.domain.run.run_repository import AgentRunRepository
from internal.domain.run.step_repository import RunStepRepository
from internal.ports import (
    CaseReadPort,
    CaseSearchPort,
    CaseWritePort,
    EventPublisherPort,
    PartitionAccessPort,
    PartitionSchemaSuggestPort,
)


@dataclass(slots=True)
class CoreProviders:
    partition_service: PartitionAccessPort
    partition_schema_suggester: PartitionSchemaSuggestPort
    case_repository: CaseReadPort
    case_service: CaseSearchPort
    case_write_service: CaseWritePort
    event_record_repository: EventRecordRepository
    event_inbox_service: KnowbaseEventInboxService
    event_publisher: EventPublisherPort
    run_repository: AgentRunRepository
    step_repository: RunStepRepository
    artifact_repository: RunArtifactRepository


@dataclass(slots=True)
class IngestProviders:
    draft_builder: KnowbaseCaseDraftBuilder
    ingestor: KnowbaseCaseIngestor
    summary_extractor: KnowbaseCaseSummaryExtractor
    semantic_profile_extractor: KnowbaseSemanticProfileExtractor
    facet_resolver: KnowbaseCaseFacetResolver


def build_core_providers() -> CoreProviders:
    partition_service = PartitionService(
        repository=PartitionRepository.from_env(),
        facet_index_repository=PartitionFacetIndexRepository.from_env(),
        facet_schema_repository=PartitionFacetSchemaRepository.from_env(),
        semantic_index_repository=PartitionSemanticIndexRepository.from_env(),
    )
    case_repository = KnowbaseCaseRepository.from_env()
    case_service = KnowbaseCaseService(repository=case_repository)
    case_write_service = KnowbaseCaseWriteService(
        repository=case_repository,
        partition_service=partition_service,
        ingestor=KnowbaseCaseIngestor(),
        facet_resolver=KnowbaseCaseFacetResolver(),
    )
    event_record_repository = EventRecordRepository.from_env()
    event_inbox_service = KnowbaseEventInboxService(repository=event_record_repository)
    event_publisher = KnowbaseEventPublisher(inbox_service=event_inbox_service)
    return CoreProviders(
        partition_service=partition_service,
        partition_schema_suggester=PartitionSchemaSuggester(),
        case_repository=case_repository,
        case_service=case_service,
        case_write_service=case_write_service,
        event_record_repository=event_record_repository,
        event_inbox_service=event_inbox_service,
        event_publisher=event_publisher,
        run_repository=AgentRunRepository.from_env(),
        step_repository=RunStepRepository.from_env(),
        artifact_repository=RunArtifactRepository.from_env(),
    )


def build_ingest_providers() -> IngestProviders:
    return IngestProviders(
        draft_builder=KnowbaseCaseDraftBuilder(),
        ingestor=KnowbaseCaseIngestor(),
        summary_extractor=KnowbaseCaseSummaryExtractor(),
        semantic_profile_extractor=KnowbaseSemanticProfileExtractor(),
        facet_resolver=KnowbaseCaseFacetResolver(),
    )
