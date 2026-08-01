"""Knowledge-local composition ports."""

from internal.knowledge.ports.projection import KnowledgeProjectionPort
from internal.knowledge.ports.governance import KnowledgeGovernancePort
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
    "KnowledgeProjectionPort",
    "KnowledgeGovernancePort",
    "KnowledgeStatisticsReaderPort",
    "KnowledgeStatisticsStorePort",
    "KnowledgeStatisticsWriterPort",
    "KnowledgeDrainPort",
]
