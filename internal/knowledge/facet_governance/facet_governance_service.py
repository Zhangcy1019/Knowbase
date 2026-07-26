"""Facet schema capability facade."""

from __future__ import annotations

from internal.knowledge.facet_governance.models import (
    FacetGovernanceResult,
    PartitionFacetCoverageAssessment,
    PartitionRebuildRecommendation,
)


class FacetGovernanceService:
    """Coordinate read-only facet governance for one Knowledge drain.

    The current implementation is a deterministic bridge used until the LLM
    governance decision is wired in. It deliberately accepts the current
    schema and never proposes a schema mutation, while still returning a
    complete governance result for the downstream projection/execution path.
    """

    def __init__(
        self,
        *,
        context_builder=None,
        metrics=None,
        key_planner=None,
        fit_metrics=None,
        freeze_policy=None,
        circuit_breaker=None,
        decision_agent=None,
    ):
        self._context_builder = context_builder
        self._metrics = metrics
        self._key_planner = key_planner
        self._fit_metrics = fit_metrics
        self._freeze_policy = freeze_policy
        self._circuit_breaker = circuit_breaker
        self._decision_agent = decision_agent

    def assess(self, *, statistics, current_schema, working_set):
        """Return a safe no-schema-change assessment without calling an LLM."""
        partition = getattr(working_set, "partition", "")
        affected_case_ids = list(getattr(working_set, "affected_case_ids", []))
        existing_keys = self._schema_keys(current_schema)
        return FacetGovernanceResult(
            coverage=PartitionFacetCoverageAssessment(
                partition=partition,
                sampled_case_ids=affected_case_ids,
                existing_keys=existing_keys,
                touched_keys=list(getattr(working_set, "affected_facet_keys", [])),
                coverage_score=1.0 if not affected_case_ids else 0.0,
                notes=["deterministic governance stub; no schema mutation proposed"],
            ),
            rebuild=PartitionRebuildRecommendation(
                partition=partition,
                rebuild_scope="partial" if affected_case_ids else "none",
                target_case_ids=affected_case_ids,
                estimated_change_count=0,
                reason="re-evaluate affected cases against the current facet schema",
            ),
            decision="accepted",
            accepted_schema=current_schema,
            requires_review=False,
            risk_level="low",
            reasons=["deterministic governance stub accepted the current schema"],
        )

    @staticmethod
    def _schema_keys(schema) -> list[str]:
        definitions = getattr(schema, "definitions", None)
        if definitions is None and isinstance(schema, dict):
            definitions = schema.get("definitions", [])
        keys: list[str] = []
        for definition in definitions or []:
            key = getattr(definition, "key", "")
            if not key and isinstance(definition, dict):
                key = definition.get("key", "")
            if key and key not in keys:
                keys.append(key)
        return keys
