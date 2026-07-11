"""Partition semantic-index document models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PartitionSemanticValueStat(BaseModel):
    value: str = ""
    count: int = 0


class PartitionSemanticKeyStat(BaseModel):
    key: str = ""
    count: int = 0
    sample_values: list[PartitionSemanticValueStat] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    last_seen_at: datetime | None = None


class PartitionSemanticIndex(BaseModel):
    partition_name: str
    key_stats: list[PartitionSemanticKeyStat] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class PartitionSemanticIndexDocument(BaseModel):
    partition_name: str
    semantic_index: PartitionSemanticIndex = Field(default_factory=lambda: PartitionSemanticIndex(partition_name=""))
    created_at: datetime
    updated_at: datetime
