"""Query normalizer skeleton."""

from __future__ import annotations

from internal.models import KnowbaseCaseSearchQuery, QueryPlan, QueryRequest


class QueryNormalizer:
    """Convert a query plan into executable repository queries."""

    def normalize_case_query(self, *, request: QueryRequest, plan: QueryPlan) -> KnowbaseCaseSearchQuery:
        return KnowbaseCaseSearchQuery(
            text=plan.search_representation or plan.normalized_text or request.text,
            partition_filters=[request.partition_name] if request.partition_name else [],
            facet_filters=plan.facet_filters,
            embedding=plan.embedding,
            size=request.size,
        )

    def normalize_lexical_case_query(self, *, request: QueryRequest, plan: QueryPlan) -> KnowbaseCaseSearchQuery:
        return KnowbaseCaseSearchQuery(
            text=plan.search_representation or plan.normalized_text or request.text,
            partition_filters=[request.partition_name] if request.partition_name else [],
            facet_filters=plan.facet_filters,
            embedding=[],
            size=max(request.size, request.recall_size),
        )

    def normalize_vector_case_query(self, *, request: QueryRequest, plan: QueryPlan) -> KnowbaseCaseSearchQuery:
        return KnowbaseCaseSearchQuery(
            text="",
            partition_filters=[request.partition_name] if request.partition_name else [],
            facet_filters=plan.facet_filters,
            embedding=plan.embedding,
            size=max(request.size, request.recall_size),
        )
