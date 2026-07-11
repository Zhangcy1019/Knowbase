"""Deterministic reranking utilities for knowbase retrieval results."""

from __future__ import annotations

from internal.models import KnowbaseCaseSearchHit, QueryPlan


class KnowbaseRanking:
    """Combine retrieval signals into one deterministic final ranking."""

    def rerank_cases(self, *, plan: QueryPlan, hits: list[KnowbaseCaseSearchHit]) -> list[KnowbaseCaseSearchHit]:
        scored_hits: list[tuple[float, KnowbaseCaseSearchHit]] = []
        query_text = (plan.normalized_text or "").strip().lower()
        query_profile_values = {
            str(value).strip().lower()
            for _, values in plan.semantic_profile.ordered_items()
            for value in values
            if str(value).strip()
        }
        query_facet_filters = {
            tuple(part.strip().lower() for part in item.split("/")[-2:])
            for item in plan.facet_filters
            if "/" in item
        }

        for hit in hits:
            document = hit.document or {}
            title = str(hit.title or document.get("title") or "").lower()
            summary = str(hit.summary_text or document.get("summary_text") or "").lower()
            hit_score = float(hit.score or 0.0)

            facet_match_count = 0
            for key, values in (hit.facets or {}).items():
                for value in values:
                    if (str(key).strip().lower(), str(value).strip().lower()) in query_facet_filters:
                        facet_match_count += 1

            hit_profile_values = {
                str(value).strip().lower()
                for values in dict(document.get("semantic_profile") or {}).values()
                if isinstance(values, list)
                for value in values
                if str(value).strip()
            }
            profile_overlap = len(query_profile_values & hit_profile_values)

            text_bonus = 0.0
            if query_text and query_text in title:
                text_bonus += 2.0
            if query_text and query_text in summary:
                text_bonus += 1.5

            final_score = hit_score + facet_match_count * 2.0 + profile_overlap * 1.5 + text_bonus
            scored_hits.append(
                (
                    final_score,
                    hit.model_copy(
                        update={
                            "score": final_score,
                            "explain": hit.explain.model_copy(
                                update={
                                    "base_score": hit_score,
                                    "final_score": final_score,
                                    "facet_match_count": facet_match_count,
                                    "profile_overlap": profile_overlap,
                                    "text_bonus": text_bonus,
                                }
                            ),
                        }
                    ),
                )
            )

        scored_hits.sort(key=lambda item: item[0], reverse=True)
        return [item[1] for item in scored_hits]
