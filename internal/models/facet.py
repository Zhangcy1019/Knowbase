"""Facet-oriented models for the new knowbase organization layer."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from internal.models.semantic_fields import SemanticFieldSet


class PartitionFacetDefinition(BaseModel):
    """Definition of one stable facet key inside a partition."""

    key: str
    display_name: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)
    enabled: bool = True


class PartitionFacetSchema(BaseModel):
    """Partition-scoped stable facet schema."""

    definitions: list[PartitionFacetDefinition] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class PartitionFacetSchemaDocument(BaseModel):
    """Persisted facet schema linked to one partition by name."""

    partition_name: str
    facet_schema: PartitionFacetSchema = Field(default_factory=PartitionFacetSchema)
    created_at: datetime
    updated_at: datetime


class CaseFacetProfile(SemanticFieldSet):
    """Stable semantic-field projection under the current partition facet schema."""

    @classmethod
    def from_semantic_profile(
        cls,
        values: dict[str, list[str]] | BaseModel | None = None,
    ) -> "CaseFacetProfile":
        return cls.model_validate(values or {})


class PartitionFacetValueStat(BaseModel):
    value: str = ""
    count: int = 0


class PartitionFacetKeyStat(BaseModel):
    key: str = ""
    count: int = 0
    sample_values: list[PartitionFacetValueStat] = Field(default_factory=list)
    last_seen_at: datetime | None = None


class PartitionFacetIndex(BaseModel):
    partition_name: str
    key_stats: list[PartitionFacetKeyStat] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class PartitionFacetIndexDocument(BaseModel):
    partition_name: str
    facet_index: PartitionFacetIndex = Field(default_factory=lambda: PartitionFacetIndex(partition_name=""))
    created_at: datetime
    updated_at: datetime


class CaseFacetValuesChangeRecord(BaseModel):
    """Audit record for one case-level facet-value change."""

    change_id: str
    partition: str
    case_id: str
    before_values: dict[str, list[str]] = Field(default_factory=dict)
    after_values: dict[str, list[str]] = Field(default_factory=dict)
    reason: str = ""
    source_event_ids: list[str] = Field(default_factory=list)
    run_id: str = ""
    created_at: datetime


class PartitionFacetValueListChangeRecord(BaseModel):
    """Audit record for one partition facet value-list change."""

    change_id: str
    partition: str
    facet_key: str
    before_values: list[str] = Field(default_factory=list)
    after_values: list[str] = Field(default_factory=list)
    added_values: list[str] = Field(default_factory=list)
    removed_values: list[str] = Field(default_factory=list)
    reason: str = ""
    source_event_ids: list[str] = Field(default_factory=list)
    run_id: str = ""
    created_at: datetime
