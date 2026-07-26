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
    PartitionTaskQueuePort,
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
    from internal.knowledge.decision import KnowledgeDecisionService
    from internal.knowledge.statistics import KnowledgeStatisticsService, QueryStatisticsService


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
    query_statistics_service: QueryStatisticsService | None = None
    decision_service: KnowledgeDecisionService | None = None
    task_queue: PartitionTaskQueuePort | None = None
