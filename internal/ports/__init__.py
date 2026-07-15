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
from internal.ports.backlog import EventBacklogPort, EventWorkerPort
from internal.ports.product import IngestUseCase, QueryUseCase
from internal.ports.knowledge import KnowledgeDispatchPort
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
    "KnowledgeDispatchPort",
    "PartitionAccessPort",
    "PartitionLookupPort",
    "PartitionSchemaSuggestPort",
    "QueryUseCase",
    "RuntimeHarnessPort",
    "RuntimeRunPort",
    "SkillExecutionPort",
]
