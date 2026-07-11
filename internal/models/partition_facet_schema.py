"""Partition facet-schema document models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from internal.models.facet import PartitionFacetSchema


class PartitionFacetSchemaDocument(BaseModel):
    """Persisted facet schema linked to one partition by name."""

    partition_name: str
    facet_schema: PartitionFacetSchema = Field(default_factory=PartitionFacetSchema)
    created_at: datetime
    updated_at: datetime
