"""Case-level schemas for knowbase."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from internal.models.common import normalize_string_list
from internal.models.facet import CaseFacetProfile
from internal.models.semantic_profile import CaseSemanticProfile
from internal.models.types import KnowbaseSource, KnowbaseStatus


class KnowbaseCaseMetadata(BaseModel):
    """Stable metadata for filtering and display."""

    author: str = ""
    source: KnowbaseSource = "user"
    status: KnowbaseStatus = "draft"


class KnowbaseCaseDraft(BaseModel):
    """Draft object produced before a case is persisted."""

    model_config = ConfigDict(populate_by_name=True)

    partition: str = ""
    title: str = ""
    source_content: str = ""
    source_refs: list[str] = Field(default_factory=list)
    summary_text: str = ""
    semantic_profile: CaseSemanticProfile = Field(default_factory=CaseSemanticProfile)
    metadata: KnowbaseCaseMetadata = Field(default_factory=KnowbaseCaseMetadata)
    facets: CaseFacetProfile = Field(default_factory=CaseFacetProfile)

    @field_validator("source_refs", mode="before")
    @classmethod
    def validate_source_refs(cls, value: Any) -> list[str]:
        return normalize_string_list(value)


class KnowbaseCaseDocument(BaseModel):
    """Canonical case document stored by knowbase."""

    model_config = ConfigDict(populate_by_name=True)

    # base info
    case_id: str
    partition: str
    created_at: datetime
    updated_at: datetime
    metadata: KnowbaseCaseMetadata = Field(default_factory=KnowbaseCaseMetadata)
    # content info
    title: str = ""
    source_content: str = ""
    source_refs: list[str] = Field(default_factory=list)
    # summary info
    summary_text: str = ""
    semantic_profile: CaseSemanticProfile = Field(default_factory=CaseSemanticProfile)
    # facet info
    facets: CaseFacetProfile = Field(default_factory=CaseFacetProfile)

    # for search
    search_text: str = ""  # built from title, facets, and semantic profile
    search_vector: list[float] = Field(default_factory=list)  # from search_text
    content_vector: list[float] = Field(default_factory=list)  # from source_content


class KnowbaseCaseSearchQuery(BaseModel):
    """Retrieval query for case-level recall."""

    model_config = ConfigDict(populate_by_name=True)

    text: str = ""
    case_ids: list[str] = Field(default_factory=list)
    partition_filters: list[str] = Field(default_factory=list)
    facet_filters: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    size: int = 10


class KnowbaseCaseSearchExplain(BaseModel):
    """Deterministic retrieval/rerank explanation for one hit."""

    branches: list[str] = Field(default_factory=list)
    lexical_score: float = 0.0
    vector_score: float = 0.0
    base_score: float = 0.0
    final_score: float = 0.0
    facet_match_count: int = 0
    profile_overlap: int = 0
    text_bonus: float = 0.0


class KnowbaseCaseSearchHit(BaseModel):
    """Normalized case search hit."""

    model_config = ConfigDict(populate_by_name=True)

    case_id: str
    score: float = 0.0
    partition: str = ""
    title: str = ""
    summary_text: str = ""
    source_excerpt: str = ""
    facets: CaseFacetProfile = Field(default_factory=CaseFacetProfile)
    explain: KnowbaseCaseSearchExplain = Field(default_factory=KnowbaseCaseSearchExplain)
    document: dict[str, Any] = Field(default_factory=dict)
