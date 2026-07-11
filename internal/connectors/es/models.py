"""Core models for ES Client"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


FilterType = Literal["must", "should"]


@dataclass(frozen=True)
class ESFieldFilter:
    """Filter definition compatible with existing es_tool contract."""

    field: str
    match_values: list[str] = field(default_factory=list)
    filter_type: FilterType = "must"
    start_time_ms: int | None = None
    end_time_ms: int | None = None


@dataclass(frozen=True)
class ESTraceRecord:
    """Normalized ES trace hit for downstream mapping."""

    doc_id: str
    timestamp_ms: int
    source: dict[str, Any]
