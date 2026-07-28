"""Deterministic circuit-breaker checks for schema proposals."""

from __future__ import annotations

from internal.knowledge.governance.validation.contracts import (
    GovernanceValidationContext,
    GovernanceValidationResult,
)


class CircuitBreaker:
    """Stop proposals whose estimated impact is too large to auto-apply."""

    def __init__(self, *, max_affected_cases: int = 100, max_schema_changes: int = 5):
        self._max_affected_cases = max_affected_cases
        self._max_schema_changes = max_schema_changes

    name = "circuit_breaker"

    def validate(self, *, context: GovernanceValidationContext) -> GovernanceValidationResult:
        evaluation = self.evaluate(
            partition=context.partition,
            patch=context.proposal,
            metrics={
                "affected_case_count": len(getattr(context.refresh_scope, "case_ids", []) or []),
            },
        )
        return GovernanceValidationResult(
            plugin=self.name,
            passed=evaluation.allowed,
            reasons=list(evaluation.reasons),
            metrics=dict(evaluation.metadata),
        )

    def evaluate(self, *, partition: str, patch, metrics):
        new_keys = list(getattr(patch, "suggested_new_keys", []) or [])
        removed_keys = list(getattr(patch, "suggested_removed_keys", []) or [])
        schema_change_count = len(new_keys) + len(removed_keys)
        affected_case_count = 0
        if metrics is not None:
            affected_case_count = int(getattr(metrics, "case_count", 0) or 0)
            if isinstance(metrics, dict):
                affected_case_count = int(metrics.get("affected_case_count", metrics.get("case_count", 0)) or 0)
        reasons: list[str] = []
        if affected_case_count > self._max_affected_cases:
            reasons.append(
                f"estimated affected case count {affected_case_count} exceeds limit {self._max_affected_cases}"
            )
        if schema_change_count > self._max_schema_changes:
            reasons.append(
                f"schema change count {schema_change_count} exceeds limit {self._max_schema_changes}"
            )
        from internal.knowledge.governance.validation.models import GovernancePolicyEvaluation

        return GovernancePolicyEvaluation(
            policy="circuit_breaker",
            allowed=not reasons,
            requires_review=bool(reasons),
            reasons=reasons,
            metadata={
                "partition": partition,
                "affected_case_count": affected_case_count,
                "schema_change_count": schema_change_count,
            },
        )
