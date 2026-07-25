"""Knowledge-owned statistics contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


StatisticsSource = Literal["case", "query"]
StatisticsField = Literal["facet", "semantic_profile", "fact"]


class StatisticsSupportFilter(BaseModel):
    """One searchable field condition for a supporting-case query."""

    field: StatisticsField
    key: str
    values: list[str] = Field(default_factory=list)


class CaseSupportQuery(BaseModel):
    """Structured query for cases supporting one or more semantic conditions."""

    filters: list[StatisticsSupportFilter] = Field(default_factory=list)
    match_mode: Literal["all", "any"] = "all"
    limit: int | None = None


class SemanticObservation(BaseModel):
    """One structured semantic observation accepted by Knowledge statistics."""

    observation_id: str
    partition: str
    source: StatisticsSource
    source_id: str
    observed_at: datetime | None = None
    facets: dict[str, list[str]] = Field(default_factory=dict)
    semantic_profile: dict[str, list[str]] = Field(default_factory=dict)
    facts: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CaseObservation(SemanticObservation):
    """Case-derived observation; case is the source of truth."""

    source: Literal["case"] = "case"


class QueryObservation(SemanticObservation):
    """Query-derived observation; query signals remain statistics-only."""

    source: Literal["query"] = "query"


class StatisticsSnapshot(BaseModel):
    """Current derived statistics for one partition.

    History is owned by the surrounding Git patch workflow. This model
    represents only the current ``snapshot.json`` working file.
    """

    partition: str
    generated_at: datetime | None = None
    source_revision: str | None = None
    case_count: int = 0
    query_count: int = 0
    case_key_stats: dict[str, int] = Field(default_factory=dict)
    query_key_stats: dict[str, int] = Field(default_factory=dict)
    value_stats: dict[str, dict[str, int]] = Field(default_factory=dict)
    case_support_index: dict[str, list[str]] = Field(default_factory=dict)
    query_support_index: dict[str, list[str]] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "CaseObservation",
    "CaseSupportQuery",
    "QueryObservation",
    "SemanticObservation",
    "StatisticsSnapshot",
    "StatisticsSupportFilter",
    "StatisticsSource",
]
