from __future__ import annotations

from dataclasses import dataclass

from internal.ports import (
    CaseReadPort,
    CaseWritePort,
    EventBacklogPort,
    EventPublisherPort,
    EventWorkerPort,
    IngestUseCase,
    PartitionAccessPort,
    PartitionSchemaSuggestPort,
    QueryUseCase,
    RuntimeRunPort,
    SkillExecutionPort,
)


@dataclass(slots=True)
class KnowbaseRouteDeps:
    partition_service: PartitionAccessPort
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
