"""Query request/result schemas for knowbase."""

from __future__ import annotations

from pydantic import BaseModel, Field

from internal.models.case import KnowbaseCaseSearchHit
from internal.models.semantic_profile import QuerySemanticProfile


class QueryRequest(BaseModel):
    """External query request accepted by knowbase."""

    text: str
    partition_name: str = ""
    size: int = 10
    recall_size: int = 30


class QueryPlan(BaseModel):
    """Multi-view query plan generated before retrieval."""

    normalized_text: str = ""
    semantic_profile: QuerySemanticProfile = Field(default_factory=QuerySemanticProfile)
    hypothetical_answer: str = ""
    search_representation: str = ""
    embedding: list[float] = Field(default_factory=list)
    use_case: bool = True
    expanded_terms: list[str] = Field(default_factory=list)
    facet_filters: list[str] = Field(default_factory=list)


class QueryAnswer(BaseModel):
    """Final answer synthesis output."""

    answer: str = ""
    citations: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning_summary: str = ""
    follow_up_questions: list[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    """Returned query result with retrieved objects and final answer."""

    plan: QueryPlan | None = None
    cases: list[KnowbaseCaseSearchHit] = Field(default_factory=list)
    answer: QueryAnswer | None = None
    debug: dict[str, object] = Field(default_factory=dict)
