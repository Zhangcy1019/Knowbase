"""Query planner skeleton."""

from __future__ import annotations

from internal.llm.embeddings import create_embedding_provider
from internal.models import PartitionFacetDefinition, QueryPlan, QueryRequest
from internal.models.partition_semantic_index import PartitionSemanticIndex
from internal.models.semantic_profile import DynamicSemanticProfile
from internal.product.query.search_representation import build_query_search_representation
from internal.product.query.semantic_profile_extractor import KnowbaseQuerySemanticProfileExtractor
from internal.utils.logger import get_logger


logger = get_logger(__name__)


class KnowbaseQueryPlanner:
    """Build a multi-view query plan for retrieval."""

    def __init__(
        self,
        semantic_profile_extractor: KnowbaseQuerySemanticProfileExtractor | None = None,
    ):
        self._semantic_profile_extractor = semantic_profile_extractor or KnowbaseQuerySemanticProfileExtractor()

    async def plan(
        self,
        request: QueryRequest,
        *,
        facet_definitions: list[PartitionFacetDefinition] | None = None,
        semantic_index: PartitionSemanticIndex | None = None,
    ) -> QueryPlan:
        semantic_profile, hypothetical_answer = await self._semantic_profile_extractor.extract(
            text=request.text,
            expanded_terms=_resolve_expanded_terms(request.text, semantic_index=semantic_index),
            facet_definitions=facet_definitions,
            semantic_index=semantic_index,
        )
        expanded_terms = _resolve_expanded_terms(request.text, semantic_index=semantic_index, semantic_profile=semantic_profile)
        facet_filters = _build_facet_filters(
            partition_name=request.partition_name,
            facet_definitions=facet_definitions or [],
            semantic_profile=semantic_profile,
        )
        search_representation = build_query_search_representation(
            text=request.text,
            partition_name=request.partition_name,
            semantic_profile=semantic_profile,
            hypothetical_answer=hypothetical_answer,
            expanded_terms=expanded_terms,
        )
        embedding: list[float] = []
        try:
            embedding = create_embedding_provider().embed_query(search_representation)
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning("Failed to build query embedding", extra={"error": str(exc)})
        return QueryPlan(
            normalized_text=request.text.strip(),
            semantic_profile=semantic_profile,
            hypothetical_answer=hypothetical_answer,
            search_representation=search_representation,
            embedding=embedding,
            route=None,
            expanded_terms=expanded_terms,
            facet_filters=facet_filters,
        )


def _resolve_expanded_terms(
    text: str,
    *,
    semantic_index: PartitionSemanticIndex | None,
    semantic_profile: DynamicSemanticProfile | None = None,
) -> list[str]:
    lowered_text = text.strip().lower()
    expanded: list[str] = []
    if semantic_profile is not None:
        for _, values in semantic_profile.ordered_items():
            for value in values:
                normalized = str(value).strip()
                if normalized and normalized.lower() not in {item.lower() for item in expanded}:
                    expanded.append(normalized)
    if semantic_index is None:
        return expanded
    for item in semantic_index.key_stats:
        normalized_key = item.key.strip()
        if not normalized_key:
            continue
        if normalized_key.lower() in lowered_text and normalized_key.lower() not in {entry.lower() for entry in expanded}:
            expanded.append(normalized_key)
        for value_stat in item.sample_values:
            normalized_value = value_stat.value.strip()
            if not normalized_value:
                continue
            if normalized_value.lower() in lowered_text and normalized_value.lower() not in {entry.lower() for entry in expanded}:
                expanded.append(normalized_value)
    return expanded[:20]


def _build_facet_filters(
    *,
    partition_name: str,
    facet_definitions: list[PartitionFacetDefinition],
    semantic_profile: DynamicSemanticProfile,
) -> list[str]:
    allowed_keys = {item.key.strip() for item in facet_definitions if item.key.strip()}
    filters: list[str] = []
    seen: set[str] = set()
    for key, _ in semantic_profile.ordered_items():
        if key not in allowed_keys:
            continue
        for value in semantic_profile.get_list(key):
            normalized = value.strip()
            if not normalized:
                continue
            item = f"{partition_name}/{key}/{normalized}"
            lowered = item.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            filters.append(item)
    return filters
