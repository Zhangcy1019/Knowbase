"""Deterministic limits for facet schema evolution."""

from __future__ import annotations

from internal.knowledge.governance.validation.contracts import (
    GovernanceValidationContext,
    GovernanceValidationResult,
)
from internal.knowledge.governance.validation.models import GovernancePolicyEvaluation


class FreezePolicy:
    """Apply bounded per-drain schema change limits.

    Historical cooldown state will be added when governance snapshots expose
    prior decisions. The first implementation still prevents one proposal from
    changing too much of the partition schema.
    """

    def __init__(self, *, max_new_keys: int = 3, max_removed_keys: int = 1):
        self._max_new_keys = max_new_keys
        self._max_removed_keys = max_removed_keys

    name = "freeze"

    def validate(self, *, context: GovernanceValidationContext) -> GovernanceValidationResult:
        evaluation = self.evaluate(partition=context.partition, proposal=context.proposal)
        return GovernanceValidationResult(
            plugin=self.name,
            passed=evaluation.allowed,
            reasons=list(evaluation.reasons),
            metrics=dict(evaluation.metadata),
        )

    def evaluate(self, *, partition: str, proposal):
        new_keys = list(getattr(proposal, "suggested_new_keys", []) or [])
        removed_keys = list(getattr(proposal, "suggested_removed_keys", []) or [])
        reasons: list[str] = []
        if len(new_keys) > self._max_new_keys:
            reasons.append(f"proposal adds {len(new_keys)} facet keys; limit is {self._max_new_keys}")
        if len(removed_keys) > self._max_removed_keys:
            reasons.append(f"proposal removes {len(removed_keys)} facet keys; limit is {self._max_removed_keys}")
        return GovernancePolicyEvaluation(
            policy="facet_freeze",
            allowed=not reasons,
            requires_review=bool(reasons),
            reasons=reasons,
            metadata={
                "partition": partition,
                "max_new_keys": self._max_new_keys,
                "max_removed_keys": self._max_removed_keys,
            },
        )
