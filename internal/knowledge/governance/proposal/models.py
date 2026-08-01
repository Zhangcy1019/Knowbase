"""Models produced by schema proposal analysis."""

from pydantic import BaseModel, Field


class PartitionFacetSchemaProposal(BaseModel):
    partition: str = ""
    rationale: str = ""
    suggested_new_keys: list[str] = Field(default_factory=list)
    suggested_removed_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
