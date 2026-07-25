"""Knowledge-local composition ports."""

from internal.knowledge.ports.patch import KnowledgePatchBuilderPort, KnowledgePatchExecutorPort
from internal.knowledge.ports.projection import KnowledgeProjectionPort
from internal.knowledge.ports.facet_governance import KnowledgeFacetGovernancePort
from internal.knowledge.ports.workflow import KnowledgeDrainPort
from internal.knowledge.ports.statistics import (
    KnowledgeStatisticsReaderPort,
    KnowledgeStatisticsStorePort,
    KnowledgeStatisticsWriterPort,
)
from internal.ports.knowledge import KnowledgeBatchNotificationPort

__all__ = [
    "KnowledgeBatchNotificationPort",
    "KnowledgeDrainPort",
    "KnowledgePatchBuilderPort",
    "KnowledgePatchExecutorPort",
    "KnowledgeProjectionPort",
    "KnowledgeFacetGovernancePort",
    "KnowledgeStatisticsReaderPort",
    "KnowledgeStatisticsStorePort",
    "KnowledgeStatisticsWriterPort",
    "KnowledgeDrainPort",
]
