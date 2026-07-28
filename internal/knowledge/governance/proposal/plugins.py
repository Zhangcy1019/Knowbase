"""Default deterministic schema-proposal plugins."""

from __future__ import annotations

from internal.knowledge.governance.proposal.contracts import (
    GovernanceProposalContext,
    GovernanceProposalPluginResult,
)


def _resolve_promotable_keys(*, existing_facet_keys, index_key_counts, index_case_count) -> list[str]:
    if index_case_count <= 0:
        return []
    threshold = max(2, int(index_case_count * 0.3))
    return sorted(key for key, count in index_key_counts.items() if key not in existing_facet_keys and count >= threshold)


def _resolve_demotable_keys(*, existing_facet_keys, observed_facet_keys, semantic_index_key_counts, facet_index_key_counts) -> list[str]:
    return sorted(
        key for key in existing_facet_keys
        if key not in observed_facet_keys
        and semantic_index_key_counts.get(key, 0) == 0
        and facet_index_key_counts.get(key, 0) == 0
    )


class SemanticKeyPromotionProposal:
    """Suggest semantic keys that have stable enough partition-wide support."""

    name = "semantic_key_promotion"

    DEFAULT_EXCLUDED_KEYS = frozenset({"title", "keywords", "actions"})

    def __init__(
        self,
        *,
        max_new_keys: int = 2,
        excluded_keys: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.max_new_keys = max(0, int(max_new_keys))
        self.excluded_keys = {
            str(key).strip().lower()
            for key in (excluded_keys if excluded_keys is not None else self.DEFAULT_EXCLUDED_KEYS)
            if str(key).strip()
        }

    def propose(self, *, context: GovernanceProposalContext) -> GovernanceProposalPluginResult:
        semantic_counts = context.statistics_semantic_key_counts or context.semantic_index_key_counts
        case_count = context.statistics_case_count or context.semantic_index_case_count
        raw_keys = _resolve_promotable_keys(
            existing_facet_keys=context.existing_facet_keys,
            index_key_counts=semantic_counts,
            index_case_count=case_count,
        )
        threshold = max(2, int(case_count * 0.3)) if case_count > 0 else 0
        excluded = [key for key in raw_keys if key.lower() in self.excluded_keys]
        eligible = [key for key in raw_keys if key.lower() not in self.excluded_keys]
        # Prefer the strongest evidence, then use a stable lexical tie-breaker
        # so proposal output is deterministic across runs.
        eligible.sort(key=lambda key: (-semantic_counts.get(key, 0), key))
        keys = eligible[: self.max_new_keys]
        limited = eligible[self.max_new_keys :]
        support_counts = {key: semantic_counts.get(key, 0) for key in keys}
        rejected_support_counts = {
            key: semantic_counts.get(key, 0) for key in [*excluded, *limited]
        }
        reasons = [
            f"{key} appears in {count}/{case_count} statistics cases, meeting the promotion threshold of {threshold}"
            for key, count in support_counts.items()
        ]
        reasons.extend(f"{key} retained as semantic-only field by default" for key in excluded)
        reasons.extend(
            f"{key} omitted because the per-drain new-key limit is {self.max_new_keys}"
            for key in limited
        )
        return GovernanceProposalPluginResult(
            plugin=self.name,
            suggested_new_keys=keys,
            reasons=reasons,
            root_cause=(
                "A semantic key is absent from the current facet schema and has enough partition-wide support to become a schema candidate."
                if keys else ""
            ),
            evidence={
                "candidate_support_counts": support_counts,
                "statistics_case_count": case_count,
                "promotion_threshold": threshold,
                "existing_facet_keys": list(context.existing_facet_keys),
                "batch_semantic_candidate_keys": list(context.semantic_candidate_keys),
                "candidate_pool": list(raw_keys),
                "excluded_semantic_keys": excluded,
                "limited_semantic_keys": limited,
                "rejected_support_counts": rejected_support_counts,
            },
            metrics={
                "threshold": threshold,
                "candidate_count": len(keys),
                "candidate_pool_count": len(raw_keys),
                "max_new_keys": self.max_new_keys,
                "excluded_key_count": len(excluded),
                "limited_key_count": len(limited),
                "candidate_support_counts": support_counts,
            },
        )


class FacetKeyDemotionProposal:
    """Suggest stable facet keys with no semantic or facet-index support."""

    name = "facet_key_demotion"

    def propose(self, *, context: GovernanceProposalContext) -> GovernanceProposalPluginResult:
        semantic_counts = context.statistics_semantic_key_counts or context.semantic_index_key_counts
        facet_counts = context.statistics_facet_key_counts or context.facet_index_key_counts
        keys = _resolve_demotable_keys(
            existing_facet_keys=context.existing_facet_keys,
            observed_facet_keys=context.observed_facet_keys,
            semantic_index_key_counts=semantic_counts,
            facet_index_key_counts=facet_counts,
        )
        support = {
            key: {
                "semantic_statistics_count": semantic_counts.get(key, 0),
                "facet_statistics_count": facet_counts.get(key, 0),
                "semantic_index_count": context.semantic_index_key_counts.get(key, 0),
                "facet_index_count": context.facet_index_key_counts.get(key, 0),
                "observed_in_batch": key in context.observed_facet_keys,
            }
            for key in keys
        }
        return GovernanceProposalPluginResult(
            plugin=self.name,
            suggested_removed_keys=keys,
            reasons=[
                f"{key} is not touched by this batch and has zero semantic-index and facet-index support"
                for key in keys
            ],
            root_cause=(
                "An existing facet key has no observed support in either index and is not involved in the current batch."
                if keys else ""
            ),
            evidence={
                "candidate_support": support,
                "observed_facet_keys": list(context.observed_facet_keys),
            },
            metrics={"candidate_count": len(keys), "candidate_support": support},
        )


__all__ = [
    "FacetKeyDemotionProposal",
    "SemanticKeyPromotionProposal",
]
