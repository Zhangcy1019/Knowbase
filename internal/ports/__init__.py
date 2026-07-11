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
    PartitionSchemaSuggestPort,
)
from internal.ports.backlog import BacklogDispatchPort, EventBacklogPort, EventWorkerPort
from internal.ports.product import IngestUseCase, QueryUseCase
from internal.ports.runtime import RuntimeHarnessPort, RuntimeRunPort, SkillExecutionPort

__all__ = [
    "BacklogDispatchPort",
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
    "PartitionAccessPort",
    "PartitionLookupPort",
    "PartitionSchemaSuggestPort",
    "QueryUseCase",
    "RuntimeHarnessPort",
    "RuntimeRunPort",
    "SkillExecutionPort",
]
