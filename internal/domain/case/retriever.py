"""Case retriever skeleton."""

from __future__ import annotations

from internal.domain.case.repository import KnowbaseCaseRepository
from internal.models import KnowbaseCaseSearchHit, KnowbaseCaseSearchQuery


class KnowbaseCaseRetriever:
    """Thin retrieval wrapper around the case repository."""

    def __init__(self, repository: KnowbaseCaseRepository):
        self._repository = repository

    def recall_lexical(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        return self._repository.search_lexical(query)

    def recall_vector(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        return self._repository.search_vector(query)
