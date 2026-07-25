"""Partition statistics capabilities and contracts."""

from internal.knowledge.statistics.models import (
    CaseObservation,
    CaseSupportQuery,
    QueryObservation,
    SemanticObservation,
    CaseStatisticsSnapshot,
    QueryStatisticsSnapshot,
    StatisticsSource,
    StatisticsSupportFilter,
)
from internal.knowledge.statistics.aggregator import StatisticsAggregator
from internal.knowledge.statistics.normalizer import StatisticsObservationNormalizer
from internal.knowledge.statistics.reader import StatisticsReader
from internal.knowledge.statistics.service import KnowledgeStatisticsService, QueryStatisticsService
from internal.knowledge.statistics.store import StatisticsStore
from internal.knowledge.statistics.writer import StatisticsWriter

__all__ = [
    "CaseObservation",
    "CaseSupportQuery",
    "KnowledgeStatisticsService",
    "QueryStatisticsService",
    "QueryObservation",
    "SemanticObservation",
    "StatisticsReader",
    "StatisticsAggregator",
    "CaseStatisticsSnapshot",
    "QueryStatisticsSnapshot",
    "StatisticsSource",
    "StatisticsStore",
    "StatisticsObservationNormalizer",
    "StatisticsSupportFilter",
    "StatisticsWriter",
]
