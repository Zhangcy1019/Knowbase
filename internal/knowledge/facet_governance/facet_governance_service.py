"""Facet schema capability facade."""

from __future__ import annotations


class FacetGovernanceService:
    """Coordinate read-only facet governance for one Knowledge drain.

    This class is intentionally only a composition boundary for now. The
    concrete context analysis, LLM decision, and deterministic safety checks
    will be added behind the injected collaborators without changing the
    workflow contract.
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
        """Return one governance assessment for the current workflow context."""
        raise NotImplementedError
