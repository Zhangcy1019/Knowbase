"""Query retrieval service with multi-branch recall and deterministic reranking."""

from __future__ import annotations

from internal.models import KnowbaseCaseSearchHit, QueryPlan, QueryRequest
from internal.ports import CaseSearchPort
from internal.product.query.normalizer import QueryNormalizer
from internal.product.query.ranking import KnowbaseRanking


class KnowbaseQueryService:
    """Execute recall branches and rerank final query candidates."""

    def __init__(
        self,
        *,
        case_service: CaseSearchPort,
        normalizer: QueryNormalizer | None = None,
        ranking: KnowbaseRanking | None = None,
    ):
        self._case_service = case_service
        self._normalizer = normalizer or QueryNormalizer()
        self._ranking = ranking or KnowbaseRanking()

    def execute(self, *, request: QueryRequest, plan: QueryPlan) -> list[KnowbaseCaseSearchHit]:
        lexical_hits = self._recall_lexical(request=request, plan=plan)
        vector_hits = self._recall_vector(request=request, plan=plan)
        merged_hits = self._merge_hits(lexical_hits=lexical_hits, vector_hits=vector_hits)
        return self._ranking.rerank_cases(plan=plan, hits=merged_hits)[: max(1, request.size)]

    def _recall_lexical(self, *, request: QueryRequest, plan: QueryPlan) -> list[KnowbaseCaseSearchHit]:
        lexical_query = self._normalizer.normalize_lexical_case_query(request=request, plan=plan)
        return self._case_service.recall_lexical(lexical_query)

    def _recall_vector(self, *, request: QueryRequest, plan: QueryPlan) -> list[KnowbaseCaseSearchHit]:
        if not plan.embedding:
            return []
        vector_query = self._normalizer.normalize_vector_case_query(request=request, plan=plan)
        return self._case_service.recall_vector(vector_query)

    @staticmethod
    def _merge_hits(
        *,
        lexical_hits: list[KnowbaseCaseSearchHit],
        vector_hits: list[KnowbaseCaseSearchHit],
    ) -> list[KnowbaseCaseSearchHit]:
        merged: dict[str, KnowbaseCaseSearchHit] = {}
        for hit in lexical_hits:
            hit = hit.model_copy(
                update={
                    "explain": hit.explain.model_copy(
                        update={
                            "branches": list(dict.fromkeys([*hit.explain.branches, "lexical"])),
                            "lexical_score": float(hit.score or 0.0),
                            "base_score": max(float(hit.explain.base_score or 0.0), float(hit.score or 0.0)),
                            "final_score": max(float(hit.explain.final_score or 0.0), float(hit.score or 0.0)),
                        }
                    )
                }
            )
            existing = merged.get(hit.case_id)
            if existing is None or hit.score > existing.score:
                merged[hit.case_id] = hit
        for hit in vector_hits:
            hit = hit.model_copy(
                update={
                    "explain": hit.explain.model_copy(
                        update={
                            "branches": list(dict.fromkeys([*hit.explain.branches, "vector"])),
                            "vector_score": float(hit.score or 0.0),
                            "base_score": max(float(hit.explain.base_score or 0.0), float(hit.score or 0.0)),
                            "final_score": max(float(hit.explain.final_score or 0.0), float(hit.score or 0.0)),
                        }
                    )
                }
            )
            existing = merged.get(hit.case_id)
            if existing is None:
                merged[hit.case_id] = hit
                continue
            merged[hit.case_id] = existing.model_copy(
                update={
                    "score": max(existing.score, hit.score),
                    "explain": existing.explain.model_copy(
                        update={
                            "branches": list(dict.fromkeys([*existing.explain.branches, *hit.explain.branches])),
                            "lexical_score": max(existing.explain.lexical_score, hit.explain.lexical_score),
                            "vector_score": max(existing.explain.vector_score, hit.explain.vector_score),
                            "base_score": max(existing.explain.base_score, hit.explain.base_score),
                            "final_score": max(existing.explain.final_score, hit.explain.final_score),
                        }
                    ),
                }
            )
        return list(merged.values())
