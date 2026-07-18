"""Case service skeleton."""

from __future__ import annotations

from internal.domain.case.retriever import KnowbaseCaseRetriever
from internal.models import KnowbaseCaseDocument, KnowbaseCaseSearchExplain, KnowbaseCaseSearchHit, KnowbaseCaseSearchQuery


class KnowbaseCaseService:
    """Case-level service used by ingest and query flows."""

    def __init__(
        self,
        *,
        repository,
        retriever: KnowbaseCaseRetriever | None = None,
    ):
        self._repository = repository
        self._retriever = retriever or KnowbaseCaseRetriever(repository)

    def store(self, document: KnowbaseCaseDocument) -> KnowbaseCaseDocument:
        return self._repository.upsert(document)

    def recall_lexical(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        return self._retriever.recall_lexical(query)

    def recall_vector(self, query: KnowbaseCaseSearchQuery) -> list[KnowbaseCaseSearchHit]:
        return self._retriever.recall_vector(query)

    def recall_by_ids(self, case_ids: list[str]) -> list[KnowbaseCaseSearchHit]:
        documents = self._repository.get_many(case_ids)
        return [
            KnowbaseCaseSearchHit(
                case_id=document.case_id,
                partition=document.partition,
                title=document.title,
                summary_text=document.summary_text,
                facets=document.facets,
                explain=KnowbaseCaseSearchExplain(),
                document=document.model_dump(mode="json"),
            )
            for document in documents
        ]
