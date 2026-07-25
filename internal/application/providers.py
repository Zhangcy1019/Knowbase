"""Provider helpers for assembling core knowbase services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from internal.infrastructure.ai.embedding_service import create_embedding_provider
from internal.domain.case.draft_builder import KnowbaseCaseDraftBuilder
from internal.domain.case.facet_resolver import KnowbaseCaseFacetResolver
from internal.domain.case.ingestor import KnowbaseCaseIngestor
from internal.domain.case.semantic_profile_extractor import KnowbaseSemanticProfileExtractor
from internal.domain.case.service import KnowbaseCaseService
from internal.domain.case.summary_extractor import KnowbaseCaseSummaryExtractor
from internal.domain.case.write_service import KnowbaseCaseWriteService
from internal.domain.event.inbox_service import KnowbaseEventInboxService
from internal.domain.event.publisher import KnowbaseEventPublisher
from internal.domain.partition.schema_suggester import PartitionSchemaSuggester
from internal.domain.partition.service import PartitionService
from internal.infrastructure.persistence import build_persistence_bundle
from internal.infrastructure.version_control.git import GitRepository
from internal.application.versioning import VersionCommitCoordinator
from internal.knowledge.statistics import (
    KnowledgeStatisticsService,
    StatisticsAggregator,
    StatisticsObservationNormalizer,
    StatisticsReader,
    StatisticsStore,
    StatisticsWriter,
)
from internal.ports import (
    CaseReadPort,
    CaseSearchPort,
    CaseWritePort,
    EventPublisherPort,
    PartitionAccessPort,
    PartitionProfileReadPort,
    PartitionSchemaSuggestPort,
)
from internal.utils.config import RuntimeConfig
from internal.utils.logger import get_logger


logger = get_logger("knowbase.application.providers")


@dataclass(slots=True)
class CoreProviders:
    runtime_cfg: RuntimeConfig
    partition_service: PartitionAccessPort
    partition_profiles: PartitionProfileReadPort
    partition_schema_suggester: PartitionSchemaSuggestPort
    case_repository: CaseReadPort
    case_service: CaseSearchPort
    case_write_service: CaseWritePort
    event_record_repository: object
    event_inbox_service: KnowbaseEventInboxService
    event_publisher: EventPublisherPort
    run_repository: object
    step_repository: object
    artifact_repository: object
    embedding_provider: object
    versioning: VersionCommitCoordinator
    statistics_service: KnowledgeStatisticsService


@dataclass(slots=True)
class IngestProviders:
    draft_builder: KnowbaseCaseDraftBuilder
    ingestor: KnowbaseCaseIngestor
    summary_extractor: KnowbaseCaseSummaryExtractor
    semantic_profile_extractor: KnowbaseSemanticProfileExtractor
    facet_resolver: KnowbaseCaseFacetResolver


def build_core_providers(*, runtime_cfg: RuntimeConfig) -> CoreProviders:
    persistence = build_persistence_bundle(runtime_cfg=runtime_cfg)
    if runtime_cfg.storage.version_control_backend != "git":
        raise ValueError(
            "unsupported storage.version_control_backend: "
            f"{runtime_cfg.storage.version_control_backend}"
        )
    version_control = GitRepository(root=Path(runtime_cfg.storage.local_root).expanduser())
    if runtime_cfg.storage.version_control_auto_init:
        try:
            version_control.initialize()
        except RuntimeError:
            logger.exception(
                "Versioned workspace is not clean; manual intervention is required before startup.",
                extra={"workspace": runtime_cfg.storage.local_root},
            )
            raise
    versioning = VersionCommitCoordinator(version_control=version_control)
    embedding_provider = create_embedding_provider(runtime_cfg.embedding)
    partition_service = PartitionService(
        repository=persistence.partition_repository,
        facet_index_repository=persistence.partition_facet_index_repository,
        facet_schema_repository=persistence.partition_facet_schema_repository,
        semantic_index_repository=persistence.partition_semantic_index_repository,
    )
    case_repository = persistence.case_repository
    case_service = KnowbaseCaseService(repository=case_repository)
    case_write_service = KnowbaseCaseWriteService(
        repository=case_repository,
        partition_service=partition_service,
        ingestor=KnowbaseCaseIngestor(),
        facet_resolver=KnowbaseCaseFacetResolver(),
        embedding_provider=embedding_provider,
    )
    event_record_repository = persistence.event_record_repository
    event_inbox_service = KnowbaseEventInboxService(repository=event_record_repository)
    event_publisher = KnowbaseEventPublisher(inbox_service=event_inbox_service)
    statistics_store = StatisticsStore(repository=persistence.statistics_snapshot_repository)
    statistics_service = KnowledgeStatisticsService(
        reader=StatisticsReader(store=statistics_store),
        writer=StatisticsWriter(
            snapshot_store=statistics_store,
            normalizer=StatisticsObservationNormalizer(),
            aggregator=StatisticsAggregator(),
        ),
        store=statistics_store,
    )
    return CoreProviders(
        runtime_cfg=runtime_cfg,
        partition_service=partition_service,
        partition_profiles=partition_service,
        partition_schema_suggester=PartitionSchemaSuggester(llm_config=runtime_cfg.llm),
        case_repository=case_repository,
        case_service=case_service,
        case_write_service=case_write_service,
        event_record_repository=event_record_repository,
        event_inbox_service=event_inbox_service,
        event_publisher=event_publisher,
        run_repository=persistence.run_repository,
        step_repository=persistence.step_repository,
        artifact_repository=persistence.artifact_repository,
        embedding_provider=embedding_provider,
        statistics_service=statistics_service,
        versioning=versioning,
    )


def build_ingest_providers(*, runtime_cfg: RuntimeConfig) -> IngestProviders:
    return IngestProviders(
        draft_builder=KnowbaseCaseDraftBuilder(),
        ingestor=KnowbaseCaseIngestor(),
        summary_extractor=KnowbaseCaseSummaryExtractor(llm_config=runtime_cfg.llm),
        semantic_profile_extractor=KnowbaseSemanticProfileExtractor(llm_config=runtime_cfg.llm),
        facet_resolver=KnowbaseCaseFacetResolver(),
    )
