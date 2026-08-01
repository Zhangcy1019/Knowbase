"""Partition fit metrics for facet schema candidates."""

from __future__ import annotations

from typing import Any

from internal.knowledge.governance.validation.contracts import (
    GovernanceValidationContext,
    GovernanceValidationResult,
)


class PartitionFitMetrics:
    """Compute bounded, deterministic fit signals for facet schema decisions.

    These defaults are deliberately conservative but not blocking by themselves.
    The governance runtime receives the result through a read-only skill and
    decides whether a candidate schema is worth accepting.
    """

    DEFAULT_MIN_COVERAGE_SCORE = 0.70
    DEFAULT_MAX_UNOBSERVED_KEYS = 2
    DEFAULT_MIN_KEY_SUPPORT = 2
    DEFAULT_MIN_KEY_SUPPORT_RATIO = 0.30
    name = "fit_metrics"

    def __init__(
        self,
        *,
        min_coverage_score: float = DEFAULT_MIN_COVERAGE_SCORE,
        max_unobserved_keys: int = DEFAULT_MAX_UNOBSERVED_KEYS,
        min_key_support: int = DEFAULT_MIN_KEY_SUPPORT,
        min_key_support_ratio: float = DEFAULT_MIN_KEY_SUPPORT_RATIO,
    ):
        self.min_coverage_score = float(min_coverage_score)
        self.max_unobserved_keys = int(max_unobserved_keys)
        self.min_key_support = int(min_key_support)
        self.min_key_support_ratio = float(min_key_support_ratio)

    def parameters(self) -> dict[str, float | int]:
        """Return the immutable policy parameters used by all fit gates."""
        return {
            "min_coverage_score": self.min_coverage_score,
            "max_unobserved_keys": self.max_unobserved_keys,
            "min_key_support": self.min_key_support,
            "min_key_support_ratio": self.min_key_support_ratio,
        }

    def validate(self, *, context: GovernanceValidationContext) -> GovernanceValidationResult:
        """Run this evaluator as a governance validation plugin."""
        statistics = self._dump_statistics(context.statistics)
        metrics = self.evaluate_candidate(
            partition=context.partition,
            current_schema=context.current_schema,
            candidate_schema=context.candidate_schema,
            semantic_key_counts=self._statistics_key_counts(statistics),
            case_count=int(statistics.get("case_count", 0) or 0),
        )
        return GovernanceValidationResult(
            plugin=self.name,
            passed=bool(metrics["passed"]),
            reasons=list(metrics["reasons"]),
            metrics=metrics,
        )

    def evaluate(self, *, partition: str, semantic_index, schema):
        existing_keys = self._schema_keys(schema)
        support = {
            str(item.key).strip(): int(item.count)
            for item in getattr(semantic_index, "key_stats", [])
            if str(item.key).strip()
        }
        observed_keys = [key for key, count in support.items() if count > 0]
        covered_keys = [key for key in existing_keys if support.get(key, 0) > 0]
        coverage_score = 1.0 if not existing_keys else round(len(covered_keys) / len(existing_keys), 2)
        return {
            "partition": partition,
            "existing_key_count": len(existing_keys),
            "observed_semantic_key_count": len(observed_keys),
            "covered_key_count": len(covered_keys),
            "coverage_score": coverage_score,
            "unobserved_existing_keys": [key for key in existing_keys if key not in covered_keys],
        }

    def evaluate_candidate(
        self,
        *,
        partition: str,
        current_schema,
        candidate_schema,
        semantic_key_counts: dict[str, int] | None = None,
        case_count: int = 0,
    ) -> dict[str, object]:
        """Evaluate whether a proposed schema remains supported by evidence."""
        current_keys = set(self._schema_keys(current_schema))
        candidate_keys = self._schema_keys(candidate_schema)
        support = {
            str(key).strip(): max(0, int(value))
            for key, value in (semantic_key_counts or {}).items()
            if str(key).strip()
        }
        observed_case_count = max(0, int(case_count))
        threshold = max(
            self.min_key_support,
            int(observed_case_count * self.min_key_support_ratio),
        ) if observed_case_count else self.min_key_support
        candidate_coverage = (
            1.0
            if not candidate_keys
            else round(sum(1 for key in candidate_keys if support.get(key, 0) > 0) / len(candidate_keys), 2)
        )
        unobserved = [key for key in candidate_keys if support.get(key, 0) <= 0]
        weak_new_keys = sorted(
            key for key in candidate_keys
            if key not in current_keys and support.get(key, 0) < threshold
        )
        reasons: list[str] = []
        if candidate_coverage < self.min_coverage_score:
            reasons.append(
                f"candidate coverage {candidate_coverage:.2f} is below {self.min_coverage_score:.2f}"
            )
        if len(unobserved) > self.max_unobserved_keys:
            reasons.append(
                f"candidate has {len(unobserved)} unobserved keys; limit is {self.max_unobserved_keys}"
            )
        if weak_new_keys:
            reasons.append(f"new keys lack minimum support: {', '.join(weak_new_keys)}")
        return {
            "partition": partition,
            "passed": not reasons,
            "reasons": reasons,
            "current_key_count": len(current_keys),
            "candidate_key_count": len(candidate_keys),
            "candidate_coverage_score": candidate_coverage,
            "unobserved_candidate_keys": unobserved,
            "weak_new_keys": weak_new_keys,
            "case_count": observed_case_count,
            "support_threshold": threshold,
            "parameters": self.parameters(),
        }

    @staticmethod
    def _dump_statistics(statistics: Any) -> dict[str, Any]:
        if hasattr(statistics, "model_dump"):
            value = statistics.model_dump(mode="json")
            return value if isinstance(value, dict) else {}
        return statistics if isinstance(statistics, dict) else {}

    @staticmethod
    def _statistics_key_counts(statistics: dict[str, Any]) -> dict[str, int]:
        value = statistics.get("case_key_stats", {})
        if not isinstance(value, dict):
            return {}
        result: dict[str, int] = {}
        for key, count in value.items():
            try:
                normalized_key = str(key).strip()
                if normalized_key.startswith("semantic_profile:"):
                    normalized_key = normalized_key.removeprefix("semantic_profile:").strip()
                if not normalized_key:
                    continue
                parsed_count = int(count)
            except (TypeError, ValueError):
                continue
            # Statistics may be exposed in both namespaced and normalized
            # forms. Treat them as the same signal rather than double-counting.
            result[normalized_key] = max(result.get(normalized_key, 0), parsed_count)
        return {key: count for key, count in result.items() if key}

    @staticmethod
    def _schema_keys(schema) -> list[str]:
        definitions = getattr(schema, "definitions", None)
        if definitions is None and isinstance(schema, dict):
            definitions = schema.get("definitions", [])
        return [
            str(getattr(item, "key", item.get("key", "") if isinstance(item, dict) else "")).strip()
            for item in definitions or []
            if str(getattr(item, "key", item.get("key", "") if isinstance(item, dict) else "")).strip()
        ]
