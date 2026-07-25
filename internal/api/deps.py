from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from internal.ports import (
    CaseReadPort,
    CaseWritePort,
    EventBacklogPort,
    EventPublisherPort,
    EventWorkerPort,
    IngestUseCase,
    PartitionReadPort,
    PartitionProfileReadPort,
    PartitionProfileWritePort,
    PartitionWritePort,
    PartitionSchemaSuggestPort,
    QueryUseCase,
    RuntimeRunPort,
    SkillExecutionPort,
)
if TYPE_CHECKING:
    from internal.versioning import VersionCommitCoordinator
    from internal.knowledge.statistics import KnowledgeStatisticsService


@dataclass(slots=True)
class KnowbaseRouteDeps:
    partition_service: PartitionReadPort | PartitionWritePort | PartitionProfileReadPort | PartitionProfileWritePort
    partition_schema_suggester: PartitionSchemaSuggestPort
    case_repository: CaseReadPort
    case_write_service: CaseWritePort
    runtime_service: RuntimeRunPort
    event_publisher: EventPublisherPort
    event_backlog_service: EventBacklogPort
    event_worker: EventWorkerPort
    skill_runtime: SkillExecutionPort
    ingest_service: IngestUseCase
    query_flow: QueryUseCase
    statistics_service: KnowledgeStatisticsService | None = None
    versioning: VersionCommitCoordinator | None = None
