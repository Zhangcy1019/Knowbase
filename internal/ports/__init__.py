"""Stable cross-module ports for knowbase."""

from internal.ports.domain import (
    CaseFacetResolutionPort,
    CaseReadPort,
    CaseRepositoryPort,
    CaseRepresentationPort,
    CaseSearchPort,
    CaseSemanticProfilePort,
    CaseStorePort,
    CaseSummaryPort,
    CaseWritePort,
    EventPublisherPort,
    PartitionAccessPort,
    PartitionLookupPort,
    PartitionProfileReadPort,
    PartitionProfileWritePort,
    PartitionReadPort,
    PartitionSchemaSuggestPort,
    PartitionWritePort,
)
from internal.ports.backlog import EventBacklogPort, EventWorkerPort
from internal.ports.product import IngestUseCase, QueryUseCase
from internal.ports.knowledge import (
    KnowledgeBatchNotificationPort,
)
from internal.ports.runtime import RuntimeHarnessPort, RuntimeRunPort, SkillExecutionPort

__all__ = [
    "CaseFacetResolutionPort",
    "CaseReadPort",
    "CaseRepositoryPort",
    "CaseRepresentationPort",
    "CaseSearchPort",
    "CaseSemanticProfilePort",
    "CaseStorePort",
    "CaseSummaryPort",
    "CaseWritePort",
    "EventBacklogPort",
    "EventPublisherPort",
    "EventWorkerPort",
    "IngestUseCase",
    "KnowledgeBatchNotificationPort",
    "PartitionAccessPort",
    "PartitionLookupPort",
    "PartitionProfileReadPort",
    "PartitionProfileWritePort",
    "PartitionReadPort",
    "PartitionSchemaSuggestPort",
    "PartitionWritePort",
    "QueryUseCase",
    "RuntimeHarnessPort",
    "RuntimeRunPort",
    "SkillExecutionPort",
]
